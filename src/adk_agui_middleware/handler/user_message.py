# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Handler for processing user messages and tool results in AGUI middleware."""

from collections.abc import Awaitable, Callable
from typing import Any

from ag_ui.core import RunAgentInput, ToolMessage, UserMessage
from fastapi import Request
from google.genai import types


class UserMessageHandler:
    """Handles processing of user messages and tool results in AGUI middleware.

    Manages user message extraction, tool result submissions, and HITL workflow transitions.
    This handler is responsible for determining whether incoming messages are new user
    requests or tool result submissions, and converting them to appropriate ADK format.

    Key Responsibilities:
    - Extract user messages from AGUI RunAgentInput
    - Detect and process tool result submissions for HITL completion
    - Convert AGUI messages to ADK format for agent processing
    - Support input conversion and transformation for custom workflows

    Attributes:
        agui_content: The incoming AGUI request containing messages and metadata
        request: HTTP request object containing additional context
        initial_state: Optional initial session state for new conversations
        convert_run_agent_input: Optional callable for custom input transformation
    """

    def __init__(
        self,
        agui_content: RunAgentInput,
        request: Request,
        initial_state: dict[str, Any] | None = None,
        convert_run_agent_input: Callable[
            [RunAgentInput, dict[str, str]], Awaitable[RunAgentInput]
        ]
        | None = None,
    ):
        """Initialize the user message handler with input data and configuration.

        Args:
            :param agui_content: AGUI input containing messages and execution parameters
            :param request: HTTP request object for context extraction
            :param initial_state: Optional initial state dictionary for new sessions
            :param convert_run_agent_input: Optional callable to transform input before processing
        """
        self.agui_content = agui_content
        self.request = request
        self.initial_state = initial_state
        self.convert_run_agent_input = convert_run_agent_input

    @property
    def thread_id(self) -> str:
        """Get the thread ID from the AGUI content.

        Returns:
            Thread identifier string
        """
        return self.agui_content.thread_id

    @property
    def is_tool_result_submission(self) -> None | ToolMessage:
        """Check if the latest message is a tool result submission.

        This property identifies HITL (Human-in-the-Loop) completion requests where
        a human is providing tool results to resume a previously paused agent execution.
        This is a key indicator for transitioning from HITL waiting state back to
        active agent processing.

        Returns:
            True if the most recent message is from a tool (HITL completion),
            False for new user requests (potential HITL initiation)

        Note:
            This determines the HITL workflow branch: completion vs. initiation.
        """
        if not self.agui_content.messages:
            return None
        return (
            self.agui_content.messages[-1]
            if isinstance(self.agui_content.messages[-1], ToolMessage)
            else None
        )

    async def init(self, tool_call_info: dict[str, str]) -> None:
        """Initialize the handler with tool call information for input conversion.

        Applies custom input conversion if configured, allowing for context-aware
        transformation of the AGUI content based on pending tool calls and session state.

        Args:
            :param tool_call_info: Dictionary mapping tool call IDs to function names
        """
        if self.convert_run_agent_input:
            self.agui_content = await self.convert_run_agent_input(
                self.agui_content, tool_call_info
            )

    def get_latest_message(self) -> types.Content | None:
        """Extract the latest user message from the AGUI content.

        Searches through messages in reverse order to find the most recent
        user message with content, converting it to ADK format for agent processing.

        Returns:
            ADK Content object containing the user message, or None if no user message found
        """
        if not self.agui_content.messages:
            return None
        for message in reversed(self.agui_content.messages):
            if isinstance(message, UserMessage) and message.content:
                return types.Content(
                    role="user", parts=[types.Part(text=message.content)]
                )
        return None
