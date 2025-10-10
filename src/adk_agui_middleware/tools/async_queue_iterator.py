from asyncio import Queue
from typing import Any


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
