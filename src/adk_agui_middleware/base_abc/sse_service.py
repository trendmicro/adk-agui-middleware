from abc import ABCMeta, abstractmethod
from collections.abc import AsyncGenerator, Callable

from ag_ui.core import BaseEvent, RunAgentInput
from ag_ui.encoder import EventEncoder
from fastapi import Request


class BaseSSEService(metaclass=ABCMeta):
    @abstractmethod
    async def get_runner(
        self, agui_content: RunAgentInput, request: Request
    ) -> Callable[[], AsyncGenerator[BaseEvent]]:
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    async def event_generator(
        self, runner: Callable[[], AsyncGenerator[BaseEvent]], encoder: EventEncoder
    ) -> AsyncGenerator[str]:
        raise NotImplementedError("This method should be implemented by subclasses.")
