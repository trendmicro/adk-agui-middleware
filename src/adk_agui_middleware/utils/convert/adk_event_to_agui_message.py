# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Conversion utilities for transforming ADK events into AGUI message format.

This module provides functionality to convert a sequence of ADK events into
structured AGUI messages suitable for conversation history display and client
consumption. It handles message accumulation, event classification, and
message type conversion.
"""

from typing import Any, cast

from ag_ui.core import (
    BaseEvent,
    TextMessageContentEvent,
    ToolCallArgsEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.core.types import (
    AssistantMessage,
    FunctionCall,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)

from ...event.agui_event import CustomThinkingTextMessageContentEvent
from ...event.agui_type import Message, ThinkingMessage


class ADKEventToAGUIMessageConverter:
    """Converts streaming ADK events into structured AGUI messages.

    This converter processes a sequence of BaseEvent and UserMessage objects
    and aggregates them into complete Message objects suitable for conversation
    history display. It handles text content accumulation, tool call assembly,
    and message type classification.

    The converter maintains an internal accumulator that groups related events
    by their identifiers and reconstructs complete messages from partial events.

    Attributes:
        accumulator: Dictionary storing partial message data keyed by event IDs
    """

    def __init__(self) -> None:
        """Initialize the converter with an empty accumulator."""
        self.accumulator: dict[str, dict[str, Any]] = {}

    def _append_content(self, key: str, msg_type: str, delta: str) -> None:
        """Append content delta to an accumulating message.

        Creates a new accumulator entry if none exists for the key,
        then appends the content delta to the existing content.

        Args:
            key: Unique identifier for the message being accumulated
            msg_type: Type of message (e.g., 'message', 'thinking')
            delta: Content fragment to append to the message
        """
        if key not in self.accumulator:
            self.accumulator[key] = {"type": msg_type, "content": ""}
        self.accumulator[key]["content"] += delta

    def _init_tool(self, key: str) -> None:
        """Initialize a tool call entry in the accumulator.

        Creates a new tool call entry with empty name and arguments
        if one doesn't already exist for the given key.

        Args:
            key: Unique identifier for the tool call (tool_call_id)
        """
        if key not in self.accumulator:
            self.accumulator[key] = {"type": "tool", "name": "", "arg": ""}

    def _classify_and_merge(
        self, messages: list[BaseEvent | UserMessage | SystemMessage]
    ) -> None:
        """Classify events by type and accumulate their data.

        Processes each event in the input list and accumulates data based on
        event type. Text content events are accumulated as deltas, tool call
        events are assembled into complete tool calls, and user messages are
        stored directly.

        Args:
            messages: List of events and messages to classify and accumulate
        """
        for event in messages:
            if isinstance(event, CustomThinkingTextMessageContentEvent):
                self._append_content(event.thinking_id, "thinking", event.delta)
            elif isinstance(event, TextMessageContentEvent):
                self._append_content(event.message_id, "message", event.delta)
            elif isinstance(event, ToolCallArgsEvent):
                self._init_tool(event.tool_call_id)
                self.accumulator[event.tool_call_id]["arg"] += event.delta
            elif isinstance(event, ToolCallStartEvent):
                self._init_tool(event.tool_call_id)
                self.accumulator[event.tool_call_id]["name"] = event.tool_call_name
            elif isinstance(event, UserMessage):
                self.accumulator[event.id] = {"type": "user", "content": event}
            elif isinstance(event, SystemMessage):
                self.accumulator[event.id] = {"type": "system", "content": event}
            elif isinstance(event, ToolCallResultEvent):
                self.accumulator[f"{event.tool_call_id}_result"] = {
                    "type": "tool_result",
                    "content": event.content,
                    "tool_call_id": event.tool_call_id,
                    "message_id": event.message_id,
                }

    @staticmethod
    def _create_message(key: str, data: dict[str, Any]) -> Message | None:  # noqa: PLR0911
        """Create a complete Message object from accumulated event data.

        Converts accumulated event data into the appropriate Message type
        based on the message type stored in the data.

        Args:
            key: Unique identifier for the message
            data: Dictionary containing accumulated message data including type and content

        Returns:
            Appropriate Message subclass instance, or None if message type is unknown
        """
        msg_type = data["type"]
        if msg_type == "thinking":
            return ThinkingMessage(role="thinking", id=key, content=data["content"])
        if msg_type == "message":
            return AssistantMessage(role="assistant", id=key, content=data["content"])
        if msg_type == "user":
            return cast(UserMessage, data.get("content"))
        if msg_type == "system":
            return cast(SystemMessage, data.get("content"))
        if msg_type == "tool":
            return AssistantMessage(
                role="assistant",
                id=key,
                tool_calls=[
                    ToolCall(
                        type="function",
                        id=key,
                        function=FunctionCall(name=data["name"], arguments=data["arg"]),
                    )
                ],
            )
        if msg_type == "tool_result":
            return ToolMessage(
                role="tool",
                id=data["message_id"],
                tool_call_id=data["tool_call_id"],
                content=data["content"],
            )
        return None

    def convert(
        self, messages: list[BaseEvent | UserMessage | SystemMessage]
    ) -> list[Message]:
        """Convert a list of events into structured AGUI messages.

        Takes a sequence of BaseEvent and UserMessage objects and converts them
        into a list of complete Message objects suitable for conversation history
        display. The conversion process accumulates partial events and assembles
        them into complete messages.

        Args:
            messages: List of events and messages to convert

        Returns:
            List of Message objects representing the complete conversation
        """
        self._classify_and_merge(messages)
        result: list[Message] = []
        for key, data in self.accumulator.items():
            if message := self._create_message(key, data):
                result.append(message)
        return result
