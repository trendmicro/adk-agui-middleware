from asyncio import Queue
from typing import Any

from ag_ui.core import BaseEvent
from google.adk.events import Event

from ..data_model.queue import EventQueue
from ..loggers.record_log import record_queue_log
from ..tools.function_name import extract_caller_name


class AsyncQueueIterator:
    def __init__(self, queue: Queue[Any]) -> None:
        self.queue = queue

    def __aiter__(self) -> "AsyncQueueIterator":
        return self

    async def __anext__(self) -> Any:
        item = await self.queue.get()
        try:
            if item is None:
                raise StopAsyncIteration
            return item
        finally:
            self.queue.task_done()


class QueueController:
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


class QueueHandler:
    def __init__(self, event_queue: EventQueue) -> None:
        self.event_queue = event_queue

    def get_adk_queue(self) -> QueueController:
        return QueueController(self.event_queue.adk_event_queue)

    def get_agui_queue(self) -> QueueController:
        return QueueController(self.event_queue.agui_event_queue)
