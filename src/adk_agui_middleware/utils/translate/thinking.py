# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Utility functions for creating thinking events and message sequences in AGUI format."""

import uuid
from collections.abc import AsyncGenerator

from ag_ui.core import EventType, ThinkingEndEvent, ThinkingStartEvent

from ...data_model.event import TranslateEvent
from ...event.agui_event import (
    CustomThinkingTextMessageContentEvent,
    CustomThinkingTextMessageEndEvent,
    CustomThinkingTextMessageStartEvent,
)


class ThinkingEventUtil:
    """Utility class for creating thinking events that represent AI reasoning processes.

    Provides static methods for generating AGUI thinking events that allow clients
    to display AI reasoning and thought processes to users.
    """

    @staticmethod
    def create_thinking_event_start() -> TranslateEvent:
        """Create a thinking start event to begin AI reasoning display.

        Returns:
            TranslateEvent containing a ThinkingStartEvent for beginning reasoning display
        """
        return TranslateEvent(
            agui_event=ThinkingStartEvent(
                type=EventType.THINKING_START,
            )
        )

    @staticmethod
    def create_thinking_event_end() -> TranslateEvent:
        """Create a thinking end event to conclude AI reasoning display.

        Returns:
            TranslateEvent containing a ThinkingEndEvent for ending reasoning display
        """
        return TranslateEvent(
            agui_event=ThinkingEndEvent(
                type=EventType.THINKING_END,
            )
        )


class ThinkingMessageEventUtil:
    """Utility class for handling thinking event translation and generation."""

    @staticmethod
    def create_thinking_message_start_event(thinking_id: str) -> TranslateEvent:
        """Create a thinking text message start event.

        Args:
            thinking_id: Unique identifier for correlating thinking message sequences

        Returns:
            TranslateEvent indicating the start of thinking text message
        """
        return TranslateEvent(
            agui_event=CustomThinkingTextMessageStartEvent(
                type=EventType.THINKING_TEXT_MESSAGE_START,
                thinking_id=thinking_id,
            )
        )

    @staticmethod
    def create_thinking_message_content_event(
        message: str, thinking_id: str
    ) -> TranslateEvent:
        """Create a thinking text message content event with the provided message.

        Args:
            message: Text content to include in the thinking event
            thinking_id: Unique identifier for correlating thinking message sequences

        Returns:
            TranslateEvent containing the thinking text message content
        """
        return TranslateEvent(
            agui_event=CustomThinkingTextMessageContentEvent(
                type=EventType.THINKING_TEXT_MESSAGE_CONTENT,
                thinking_id=thinking_id,
                delta=message,
            )
        )

    @staticmethod
    def create_thinking_message_end_event(thinking_id: str) -> TranslateEvent:
        """Create a thinking text message end event.

        Args:
            thinking_id: Unique identifier for correlating thinking message sequences

        Returns:
            TranslateEvent indicating the end of thinking text message
        """
        return TranslateEvent(
            agui_event=CustomThinkingTextMessageEndEvent(
                type=EventType.THINKING_TEXT_MESSAGE_END,
                thinking_id=thinking_id,
            )
        )

    async def generate_thinking_message_event(
        self, message: str, uid: str | None = None
    ) -> AsyncGenerator[TranslateEvent]:
        """Generate a complete thinking message event sequence.

        Creates the full sequence of thinking events: start, content, and end events
        for displaying a single thinking message to the user.

        Args:
            message: Text content to display as thinking message
            uid: Optional unique identifier for the thinking sequence, generated if None

        Yields:
            TranslateEvent objects for start, content, and end of thinking message
        """
        uid = uid if uid else str(uuid.uuid4())
        yield self.create_thinking_message_start_event(uid)
        yield self.create_thinking_message_content_event(message, uid)
        yield self.create_thinking_message_end_event(uid)

    async def generate_thinking_message_event_with_generator(
        self, message: AsyncGenerator[str], uid: str | None = None
    ) -> AsyncGenerator[TranslateEvent]:
        """Generate a sequence of thinking events from an async message stream.

        Yields start event, content events for each message chunk, and end event.

        Args:
            message: Async generator yielding text chunks
            uid: Optional unique identifier for the thinking sequence, generated if None

        Yields:
            TranslateEvent objects representing thinking events sequence (start, content chunks, end)
        """
        uid = uid if uid else str(uuid.uuid4())
        yield self.create_thinking_message_start_event(uid)
        async for text_chunk in message:
            yield self.create_thinking_message_content_event(text_chunk, uid)
        yield self.create_thinking_message_end_event(uid)
