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
    """

    thinking_id: str
    """Unique identifier for correlating thinking message sequences."""


class CustomThinkingTextMessageContentEvent(ThinkingTextMessageContentEvent):
    """Extended thinking text message content event with custom thinking ID tracking.

    Extends the base ThinkingTextMessageContentEvent to include a custom thinking_id
    field for enhanced tracking and correlation of thinking message content.
    """

    thinking_id: str
    """Unique identifier for correlating thinking message sequences."""


class CustomThinkingTextMessageEndEvent(ThinkingTextMessageEndEvent):
    """Extended thinking text message end event with custom thinking ID tracking.

    Extends the base ThinkingTextMessageEndEvent to include a custom thinking_id
    field for enhanced tracking and correlation of thinking message sequences.
    """

    thinking_id: str
    """Unique identifier for correlating thinking message sequences."""


class CustomMessagesSnapshotEvent(BaseEvent):
    """
    Event containing a snapshot of the messages.
    """

    type: Literal[EventType.MESSAGES_SNAPSHOT] = EventType.MESSAGES_SNAPSHOT  # pyright: ignore[reportIncompatibleVariableOverride]
    messages: list[Message]
