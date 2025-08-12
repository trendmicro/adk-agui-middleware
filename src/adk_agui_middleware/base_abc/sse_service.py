"""Abstract base class for Server-Sent Events service implementations."""

from abc import ABCMeta, abstractmethod
from collections.abc import AsyncGenerator, Callable

from ag_ui.core import BaseEvent, RunAgentInput
from ag_ui.encoder import EventEncoder
from fastapi import Request


class BaseSSEService(metaclass=ABCMeta):
    """Abstract base class defining the interface for SSE service implementations.

    Provides the contract for services that handle agent execution and event streaming
    through Server-Sent Events protocol.
    """

    @abstractmethod
    async def get_runner(
        self, agui_content: RunAgentInput, request: Request
    ) -> Callable[[], AsyncGenerator[BaseEvent]]:
        """Create and configure an agent runner for the given request.

        Args:
            agui_content: Input containing agent execution parameters
            request: HTTP request containing client context

        Returns:
            Callable that returns an async generator of BaseEvent objects

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    async def event_generator(
        self, runner: Callable[[], AsyncGenerator[BaseEvent]], encoder: EventEncoder
    ) -> AsyncGenerator[str]:
        """Generate encoded event strings from the agent runner.

        Takes the runner and encoder to produce a stream of encoded event strings
        suitable for Server-Sent Events transmission.

        Args:
            runner: Callable that returns an async generator of events
            encoder: Event encoder for formatting events according to client requirements

        Yields:
            Encoded event strings ready for SSE transmission

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
