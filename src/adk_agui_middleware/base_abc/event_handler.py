from abc import ABCMeta, abstractmethod
from collections.abc import AsyncGenerator

from google.adk.events import Event


class BaseEventHandler(metaclass=ABCMeta):
    @abstractmethod
    async def run_async(self, event: Event) -> AsyncGenerator[Event, None]:
        raise NotImplementedError("Subclasses must implement this method.")
