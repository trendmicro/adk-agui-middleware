from collections.abc import AsyncGenerator

from ag_ui.core import (
    EventType,
    ThinkingTextMessageContentEvent,
    ThinkingTextMessageEndEvent,
    ThinkingTextMessageStartEvent,
)

from ...data_model.event import TranslateEvent


class ThinkingEventUtil:
    """Utility class for handling thinking event translation and generation."""

    @staticmethod
    def thinking_start_event() -> TranslateEvent:
        """Create a thinking text message start event.

        Returns:
            TranslateEvent: Event indicating the start of thinking text message.
        """
        return TranslateEvent(
            agui_event=ThinkingTextMessageStartEvent(
                type=EventType.THINKING_TEXT_MESSAGE_START,
            )
        )

    @staticmethod
    def thinking_content_event(message: str) -> TranslateEvent:
        """Create a thinking text message content event with the provided message.

        Args:
            message: Text content to include in the thinking event.

        Returns:
            TranslateEvent: Event containing the thinking text message content.
        """
        return TranslateEvent(
            agui_event=ThinkingTextMessageContentEvent(
                type=EventType.THINKING_TEXT_MESSAGE_CONTENT,
                delta=message,
            )
        )

    @staticmethod
    def thinking_end_event() -> TranslateEvent:
        """Create a thinking text message end event.

        Returns:
            TranslateEvent: Event indicating the end of thinking text message.
        """
        return TranslateEvent(
            agui_event=ThinkingTextMessageEndEvent(
                type=EventType.THINKING_TEXT_MESSAGE_END,
            )
        )

    async def think_event_generator(
        self, message: AsyncGenerator[str]
    ) -> AsyncGenerator[TranslateEvent]:
        """Generate a sequence of thinking events from an async message stream.

        Yields start event, content events for each message chunk, and end event.

        Args:
            message: Async generator yielding text chunks.

        Yields:
            TranslateEvent: Sequence of thinking events (start, content chunks, end).
        """
        yield self.thinking_start_event()
        async for text_chunk in message:
            yield self.thinking_content_event(text_chunk)
        yield self.thinking_end_event()
