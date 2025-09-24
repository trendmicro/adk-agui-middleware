# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Handler for processing user messages and tool results in AGUI middleware."""

from collections.abc import Awaitable, Callable
from typing import Any

from ag_ui.core import RunAgentInput, ToolMessage, UserMessage
from fastapi import Request
from google.genai import types


class UserMessageHandler:
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
        if self.convert_run_agent_input:
            self.agui_content = await self.convert_run_agent_input(
                self.agui_content, tool_call_info
            )

    def get_latest_message(self) -> types.Content | None:
        if not self.agui_content.messages:
            return None
        for message in reversed(self.agui_content.messages):
            if isinstance(message, UserMessage) and message.content:
                return types.Content(
                    role="user", parts=[types.Part(text=message.content)]
                )
        return None
