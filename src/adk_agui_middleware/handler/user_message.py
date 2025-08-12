import json
from typing import Any

from ag_ui.core import AssistantMessage, RunAgentInput, ToolMessage
from google.genai import types
from loggers.record_log import record_error_log, record_log, record_warning_log
from fastapi import Request


class UserMessageHandler:
    def __init__(self, agui_content: RunAgentInput, request: Request, initial_state: dict[str, str] | None = None):
        self.agui_content = agui_content
        self.request = request
        self.initial_state = initial_state

    @property
    def thread_id(self) -> str:
        return self.agui_content.thread_id

    @property
    def initial_state(self) -> dict[str, str] | None:
        return self.initial_state

    @property
    def is_tool_result_submission(self) -> bool:
        if not self.agui_content.messages:
            return False
        return self.agui_content.messages[-1].role == "tool"

    @staticmethod
    def _parse_tool_content(content: str, tool_call_id: str) -> dict[str, str | None]:
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
        if not self.agui_content.messages:
            return None
        for message in reversed(self.agui_content.messages):
            if message.role == "user" and message.content:
                return types.Content(
                    role="user", parts=[types.Part(text=message.content)]
                )
        return None

    async def extract_tool_results(self) -> list[dict[str, Any]]:
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
        return await self.process_tool_results() or await self.get_latest_message()
