from abc import ABCMeta, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from ag_ui.core import BaseEvent
from google.adk.events import Event

from ..data_model.event import TranslateEvent
from ..tools.event_translator import EventTranslator


class BaseTranslateHandler(metaclass=ABCMeta):
    def __init__(self, event_translator: EventTranslator):
        self.event_translator = event_translator

    @abstractmethod
    def translate(self, adk_event: Event) -> AsyncGenerator[TranslateEvent]:
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseADKEventHandler(metaclass=ABCMeta):
    @abstractmethod
    async def process(self, event: Event) -> AsyncGenerator[Event]:
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseAGUIEventHandler(metaclass=ABCMeta):
    @abstractmethod
    async def process(self, event: BaseEvent) -> AsyncGenerator[BaseEvent]:
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseAGUIStateSnapshotHandler(metaclass=ABCMeta):
    @abstractmethod
    async def process(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("This method should be implemented by subclasses.")
