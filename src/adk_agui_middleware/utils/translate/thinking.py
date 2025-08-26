"""Utility functions for creating thinking events and message sequences in AGUI format."""

import uuid
from collections.abc import AsyncGenerator

from ag_ui.core import (
    EventType,
    ThinkingEndEvent,
    ThinkingStartEvent,
)
from event.agui_event import (
    CustomerThinkingTextMessageContentEvent,
    CustomerThinkingTextMessageEndEvent,
    CustomerThinkingTextMessageStartEvent,
)

from ...data_model.event import TranslateEvent


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

        Returns:
            TranslateEvent: Event indicating the start of thinking text message.
        """
        return TranslateEvent(
            agui_event=CustomerThinkingTextMessageStartEvent(
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
            message: Text content to include in the thinking event.

        Returns:
            TranslateEvent: Event containing the thinking text message content.
            :param message:
            :param thinking_id:
        """
        return TranslateEvent(
            agui_event=CustomerThinkingTextMessageContentEvent(
                type=EventType.THINKING_TEXT_MESSAGE_CONTENT,
                thinking_id=thinking_id,
                delta=message,
            )
        )

    @staticmethod
    def create_thinking_message_end_event(thinking_id: str) -> TranslateEvent:
        """Create a thinking text message end event.

        Returns:
            TranslateEvent: Event indicating the end of thinking text message.
        """
        return TranslateEvent(
            agui_event=CustomerThinkingTextMessageEndEvent(
                type=EventType.THINKING_TEXT_MESSAGE_END,
                thinking_id=thinking_id,
            )
        )

    async def create_thinking_message_event(
        self, message: str
    ) -> AsyncGenerator[TranslateEvent]:
        """Generate a complete thinking message event sequence.

        Creates the full sequence of thinking events: start, content, and end events
        for displaying a single thinking message to the user.

        Args:
            message: Text content to display as thinking message

        Yields:
            TranslateEvent objects for start, content, and end of thinking message
        """
        uid = str(uuid.uuid4())
        yield self.create_thinking_message_start_event(uid)
        yield self.create_thinking_message_content_event(message, uid)
        yield self.create_thinking_message_end_event(uid)

    async def create_thinking_message_event_with_generator(
        self, message: AsyncGenerator[str]
    ) -> AsyncGenerator[TranslateEvent]:
        """Generate a sequence of thinking events from an async message stream.

        Yields start event, content events for each message chunk, and end event.

        Args:
            message: Async generator yielding text chunks.

        Yields:
            TranslateEvent: Sequence of thinking events (start, content chunks, end)
        """
        uid = str(uuid.uuid4())
        yield self.create_thinking_message_start_event(uid)
        async for text_chunk in message:
            yield self.create_thinking_message_content_event(text_chunk, uid)
        yield self.create_thinking_message_end_event(uid)
