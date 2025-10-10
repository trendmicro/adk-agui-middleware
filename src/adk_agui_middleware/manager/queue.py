# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Queue manager providing logging and iteration support for event queues."""

from asyncio import Queue
from typing import Any

from ag_ui.core import BaseEvent
from google.adk.events import Event

from ..loggers.record_log import record_queue_log
from ..tools.async_queue_iterator import AsyncQueueIterator
from ..tools.function_name import extract_caller_name


class QueueManager:
    """Manages event queue operations with integrated logging and iteration support.

    Wraps asyncio Queue instances to provide:
    - Automatic logging of queue operations for debugging and monitoring
    - Async iterator adapter for natural queue consumption patterns
    - Caller tracking for tracing event flow through the pipeline

    This manager is used for both ADK and AGUI event queues, providing
    consistent queue operation patterns throughout the middleware.

    Attributes:
        queue: The underlying asyncio Queue being managed
    """

    def __init__(self, queue: Queue[Any]) -> None:
        """Initialize the queue manager with an asyncio Queue.

        Args:
            :param queue: Asyncio Queue to manage
        """
        self.queue = queue

    async def put(self, event: Event | BaseEvent | None) -> None:
        """Add an event to the queue with automatic logging.

        Logs the event type and caller information before adding to the queue.
        This provides visibility into event flow for debugging and monitoring.
        None events are logged as termination signals.

        Args:
            :param event: Event to add to the queue (ADK Event, AGUI BaseEvent, or None sentinel)
        """
        record_queue_log(
            {
                "call_function": extract_caller_name(),
                "type": type(event).__name__ if event is not None else "NoneType",
                "event": event,
            }
        )
        await self.queue.put(event)

    def get_iterator(self) -> AsyncQueueIterator:
        """Get an async iterator for consuming queue items.

        Creates an AsyncQueueIterator wrapping this queue, enabling consumption
        with async for loops. The iterator automatically handles queue termination
        when None is encountered.

        Returns:
            AsyncQueueIterator for consuming queue items with async for
        """
        return AsyncQueueIterator(self.queue)
