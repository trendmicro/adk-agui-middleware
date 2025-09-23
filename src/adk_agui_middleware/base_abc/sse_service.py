# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Abstract base class for Server-Sent Events service implementations."""

from abc import ABCMeta, abstractmethod
from collections.abc import AsyncGenerator, Callable

from ag_ui.core import BaseEvent, RunAgentInput
from fastapi import Request

from ..base_abc.handler import BaseInOutHandler
from ..data_model.common import InputInfo


class BaseSSEService(metaclass=ABCMeta):
    """Abstract base class defining the interface for SSE service implementations.

    Provides the contract for services that handle agent execution and event streaming
    through Server-Sent Events protocol. This interface defines the core methods
    required for processing AGUI requests and generating streaming responses with
    proper context extraction and event encoding.
    """

    @abstractmethod
    async def get_runner(
        self, agui_content: RunAgentInput, request: Request
    ) -> tuple[
        Callable[[], AsyncGenerator[BaseEvent]],
        InputInfo,
        BaseInOutHandler | None,
    ]:
        """Create and configure an agent runner for the given request.

        Extracts context from the request, initializes handlers and managers,
        and returns a configured runner function that generates agent events.
        This method handles all the setup required for agent execution.

        Args:
            :param agui_content: Input containing agent execution parameters and message content
            :param request: HTTP request containing client context and headers

        Returns:
            Tuple containing the runner callable and optional input/output handler

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    async def event_generator(
        self,
        runner: Callable[[], AsyncGenerator[BaseEvent]],
        input_info: InputInfo,
        inout_handler: BaseInOutHandler | None = None,
    ) -> AsyncGenerator[dict[str, str]]:
        """Generate encoded event strings from the agent runner.

        Takes the runner and executes it to produce a stream of encoded event
        dictionaries suitable for Server-Sent Events transmission. Handles event
        encoding, error recovery, and optional input/output processing.

        Args:
            :param runner: Callable that returns an async generator of BaseEvent objects
            :param inout_handler: Optional handler for input/output recording and transformation

        Yields:
            Encoded event dictionaries ready for SSE transmission

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
