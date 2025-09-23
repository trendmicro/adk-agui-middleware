# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Custom AGUI thinking event implementations with enhanced tracking capabilities."""

from typing import Literal

from ag_ui.core import (
    BaseEvent,
    EventType,
    ThinkingTextMessageContentEvent,
    ThinkingTextMessageEndEvent,
    ThinkingTextMessageStartEvent,
)

from ..event.agui_type import Message


class CustomThinkingTextMessageStartEvent(ThinkingTextMessageStartEvent):
    """Extended thinking text message start event with custom thinking ID tracking.

    Extends the base ThinkingTextMessageStartEvent to include a custom thinking_id
    field for enhanced tracking and correlation of thinking message sequences.
    This enables better debugging and monitoring of agent reasoning processes.
    """

    thinking_id: str
    """Unique identifier for correlating thinking message sequences."""


class CustomThinkingTextMessageContentEvent(ThinkingTextMessageContentEvent):
    """Extended thinking text message content event with custom thinking ID tracking.

    Extends the base ThinkingTextMessageContentEvent to include a custom thinking_id
    field for enhanced tracking and correlation of thinking message content.
    This enables streaming of agent reasoning with proper sequence correlation.
    """

    thinking_id: str
    """Unique identifier for correlating thinking message sequences."""


class CustomThinkingTextMessageEndEvent(ThinkingTextMessageEndEvent):
    """Extended thinking text message end event with custom thinking ID tracking.

    Extends the base ThinkingTextMessageEndEvent to include a custom thinking_id
    field for enhanced tracking and correlation of thinking message sequences.
    This completes the thinking message sequence for proper client handling.
    """

    thinking_id: str
    """Unique identifier for correlating thinking message sequences."""


class CustomMessagesSnapshotEvent(BaseEvent):
    """Event containing a snapshot of the conversation messages.

    Provides a complete snapshot of all messages in a conversation thread,
    enabling clients to reconstruct conversation history or synchronize
    their local state with the server's conversation data.

    Attributes:
        type: Event type identifier (MESSAGES_SNAPSHOT)
        messages: List of Message objects representing the conversation history
    """

    type: Literal[EventType.MESSAGES_SNAPSHOT] = EventType.MESSAGES_SNAPSHOT  # pyright: ignore[reportIncompatibleVariableOverride]
    messages: list[Message]
