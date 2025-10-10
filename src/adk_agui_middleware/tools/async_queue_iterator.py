# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Async iterator wrapper for asyncio Queue enabling async for loop consumption."""

from asyncio import Queue
from typing import Any


class AsyncQueueIterator:
    """Async iterator adapter for asyncio.Queue enabling async for loop patterns.

    Wraps an asyncio Queue to provide async iterator protocol (__aiter__ and __anext__),
    allowing queues to be consumed naturally with async for loops. Treats None as a
    sentinel value to signal iteration termination, which enables clean producer-consumer
    shutdown patterns.

    This iterator automatically calls task_done() on the queue after retrieving each item,
    properly integrating with Queue.join() synchronization if needed.

    Attributes:
        queue: The asyncio Queue to iterate over
    """

    def __init__(self, queue: Queue[Any]) -> None:
        """Initialize the async queue iterator.

        Args:
            :param queue: Asyncio Queue to wrap with iterator protocol
        """
        self.queue = queue

    def __aiter__(self) -> "AsyncQueueIterator":
        """Return the iterator object (self) for async for protocol.

        Returns:
            Self reference for async iteration protocol
        """
        return self

    async def __anext__(self) -> Any:
        """Get the next item from the queue, stopping on None sentinel.

        Retrieves the next item from the queue, treating None as a termination signal.
        Automatically marks the task as done on the queue after retrieval, supporting
        proper queue synchronization patterns.

        Returns:
            Next item from the queue

        Raises:
            StopAsyncIteration: When None is encountered (signals end of iteration)
        """
        item = await self.queue.get()
        try:
            if item is None:
                raise StopAsyncIteration
            return item
        finally:
            self.queue.task_done()
