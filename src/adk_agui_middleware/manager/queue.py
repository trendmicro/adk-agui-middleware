from asyncio import Queue
from typing import Any

from ag_ui.core import BaseEvent
from google.adk.events import Event

from ..loggers.record_log import record_queue_log
from ..tools.async_queue_iterator import AsyncQueueIterator
from ..tools.function_name import extract_caller_name


class QueueManager:
    def __init__(self, queue: Queue[Any]) -> None:
        self.queue = queue

    async def put(self, event: Event | BaseEvent | None) -> None:
        record_queue_log(
            {
                "call_function": extract_caller_name(),
                "type": type(event).__name__ if event is not None else "NoneType",
                "event": event,
            }
        )
        await self.queue.put(event)

    def get_iterator(self) -> AsyncQueueIterator:
        return AsyncQueueIterator(self.queue)
