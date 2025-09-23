# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Utility functions for creating text message events in AGUI format.

This module provides utilities for generating complete text message event sequences
including start, content, and end events for display in the AGUI interface.
"""

from collections.abc import AsyncGenerator

from ag_ui.core import (
    BaseEvent,
    EventType,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)

from ...event.agui_event import CustomMessagesSnapshotEvent
from ...event.agui_type import Message


class MessageEventUtil:
    """Utility class for generating complete text message event sequences.

    Provides static methods for creating AGUI text message events that follow
    the standard pattern of start -> content -> end for proper message display.
    """

    @staticmethod
    async def generate_message_event(
        message_id: str, message: str
    ) -> AsyncGenerator[BaseEvent]:
        """Generate a complete text message event sequence.

        Creates the standard three-event sequence for displaying a text message:
        TextMessageStartEvent, TextMessageContentEvent, and TextMessageEndEvent.
        This ensures proper message boundaries and consistent formatting.

        Args:
            message_id: Unique identifier for the message
            message: Text content to display in the message

        Yields:
            BaseEvent objects for the complete message sequence
        """
        yield TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START, message_id=message_id, role="assistant"
        )
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT, message_id=message_id, delta=message
        )
        yield TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END, message_id=message_id
        )

    @staticmethod
    def create_message_snapshot(
        message_list: list[Message] | None,
    ) -> CustomMessagesSnapshotEvent:
        """Create a message snapshot event from a list of messages.

        Converts a list of Message objects into a MessagesSnapshotEvent
        for sending conversation history to clients.

        Args:
            message_list: List of Message objects to include in snapshot, or None

        Returns:
            MessagesSnapshotEvent containing the messages (empty if None provided)
        """
        return CustomMessagesSnapshotEvent(
            type=EventType.MESSAGES_SNAPSHOT, messages=message_list or []
        )
