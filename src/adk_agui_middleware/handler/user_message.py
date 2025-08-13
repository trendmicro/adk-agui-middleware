"""Handler for processing user messages and tool results in AGUI middleware."""

import json
from typing import Any

from ag_ui.core import AssistantMessage, RunAgentInput, ToolMessage
from fastapi import Request
from google.genai import types
from loggers.record_log import record_error_log, record_log, record_warning_log


class UserMessageHandler:
    """Handles processing of user messages and tool results for agent execution.

    Manages extraction and conversion of user messages, tool calls, and tool results
    from AGUI format to Google GenAI format for agent processing.
    """

    def __init__(
        self,
        agui_content: RunAgentInput,
        request: Request,
        initial_state: dict[str, str] | None = None,
    ):
        """Initialize the user message handler.

        Args:
            agui_content: Input containing agent execution parameters and messages
            request: HTTP request for additional context
            initial_state: Optional initial state dictionary
        """
        self.agui_content = agui_content
        self.request = request
        self.initial_state = initial_state

    @property
    def thread_id(self) -> str:
        """Get the thread ID from the AGUI content.

        Returns:
            Thread identifier string
        """
        return self.agui_content.thread_id

    @property
    def is_tool_result_submission(self) -> bool:
        """Check if the latest message is a tool result submission.

        Returns:
            True if the most recent message is from a tool, False otherwise
        """
        if not self.agui_content.messages:
            return False
        return self.agui_content.messages[-1].role == "tool"

    @staticmethod
    def _parse_tool_content(content: str, tool_call_id: str) -> dict[str, str | None]:
        """Parse tool result content, handling empty content and JSON errors.

        Args:
            content: Raw tool result content string
            tool_call_id: Identifier of the tool call for logging

        Returns:
            Dictionary containing parsed tool result or error information
        """
        if not content or not content.strip():
            record_warning_log(
                f"Empty tool result content for tool call {tool_call_id}, using empty success result"
            )
            return {"success": True, "result": None}
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            record_error_log("Invalid JSON in tool result", e)
            return {
                "error": f"Invalid JSON in tool result: {str(e)}",
                "raw_content": content,
                "error_type": "JSON_DECODE_ERROR",
            }

    async def get_latest_message(self) -> types.Content | None:
        """Extract the most recent user message from the conversation.

        Searches backwards through messages to find the latest user message
        with non-empty content.

        Returns:
            Google GenAI Content object for the latest user message, or None
        """
        if not self.agui_content.messages:
            return None
        for message in reversed(self.agui_content.messages):
            if message.role == "user" and message.content:
                return types.Content(
                    role="user", parts=[types.Part(text=message.content)]
                )
        return None

    async def extract_tool_results(self) -> list[dict[str, Any]]:
        """Extract the most recent tool result from the message history.

        Finds the latest tool message and maps it to its corresponding tool name
        using the tool call history from assistant messages.

        Returns:
            List containing tool result dictionary with tool name and message,
            or empty list if no tool messages found
        """
        most_recent_tool_message = next(
            (
                msg
                for msg in reversed(self.agui_content.messages)
                if isinstance(msg, ToolMessage)
            ),
            None,
        )
        if not most_recent_tool_message:
            return []

        tool_call_map = {
            tool_call.id: tool_call.function.name
            for msg in self.agui_content.messages
            if isinstance(msg, AssistantMessage) and msg.tool_calls
            for tool_call in msg.tool_calls
        }
        tool_name = tool_call_map.get(most_recent_tool_message.tool_call_id, "unknown")
        record_log(
            f"Extracted most recent ToolMessage: role={most_recent_tool_message.role}, "
            f"tool_call_id={most_recent_tool_message.tool_call_id}, "
            f"content='{most_recent_tool_message.content}'"
        )
        return [{"tool_name": tool_name, "message": most_recent_tool_message}]

    async def process_tool_results(self) -> types.Content | None:
        """Process tool results and convert to Google GenAI Content format.

        Extracts tool results, parses their content, and creates function response
        parts for the agent to process.

        Returns:
            Google GenAI Content object with function responses, or None if no tool results
        """
        if not self.is_tool_result_submission:
            return None
        parts = []
        for tool_msg in await self.extract_tool_results():
            tool_call_id = tool_msg["message"].tool_call_id
            content = tool_msg["message"].content
            result = self._parse_tool_content(content, tool_call_id)
            parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        id=tool_call_id,
                        name=tool_msg["tool_name"],
                        response=result,
                    )
                )
            )
        return types.Content(parts=parts, role="user")

    async def get_message(self) -> types.Content | None:
        """Get the appropriate message content for agent processing.

        Returns tool results if this is a tool result submission, otherwise
        returns the latest user message.

        Returns:
            Google GenAI Content object for agent processing, or None
        """
        return await self.process_tool_results() or await self.get_latest_message()
