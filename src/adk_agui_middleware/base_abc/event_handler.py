from abc import ABCMeta, abstractmethod
from collections.abc import AsyncGenerator

from ag_ui.core import BaseEvent
from google.adk.events import Event


class BaseEventHandler(metaclass=ABCMeta):
    @abstractmethod
    async def run_async(self, event: Event | BaseEvent) -> AsyncGenerator[Event, None]:
        raise NotImplementedError("Subclasses must implement this method.")
