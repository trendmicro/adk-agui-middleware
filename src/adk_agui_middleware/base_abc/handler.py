"""Abstract base classes for event and state handlers in the middleware."""

from abc import ABCMeta, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from ag_ui.core import BaseEvent, RunAgentInput
from fastapi import Request
from google.adk.events import Event

from ..data_model.event import TranslateEvent


class BaseTranslateHandler(metaclass=ABCMeta):
    """Abstract base class for event translation handlers.

    Handles translation of ADK events to AGUI events using the provided event translator.
    """

    @abstractmethod
    async def translate(self, adk_event: Event) -> AsyncGenerator[TranslateEvent]:
        """Translate an ADK event to AGUI event format.

        Args:
            adk_event: The ADK event to be translated

        Yields:
            TranslateEvent objects representing the translated events

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseADKEventHandler(metaclass=ABCMeta):
    """Abstract base class for ADK event processing handlers.

    Defines the interface for handlers that process ADK events and potentially
    transform or filter them before further processing.
    """

    @abstractmethod
    async def process(self, event: Event) -> AsyncGenerator[Event | None]:
        """Process an ADK event and yield resulting events.

        Args:
            event: The ADK event to process

        Yields:
            Processed Event objects

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseADKEventTimeoutHandler(metaclass=ABCMeta):
    """Abstract base class for handling ADK event timeouts and fallback processing.

    Defines the interface for handlers that manage timeout behavior in event processing,
    including timeout duration configuration and fallback event generation when timeouts occur.
    """

    @abstractmethod
    async def get_timeout(self) -> int:
        """Get the timeout duration in seconds for event processing.

        Returns:
            Timeout duration in seconds

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    async def process_timeout_fallback(self) -> AsyncGenerator[Event | None]:
        """Process timeout fallback and generate appropriate events.

        Called when event processing exceeds the configured timeout duration.
        Should generate fallback events to handle the timeout gracefully.

        Yields:
            Event objects to be processed as timeout fallback

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseAGUIEventHandler(metaclass=ABCMeta):
    """Abstract base class for AGUI event processing handlers.

    Defines the interface for handlers that process AGUI events and potentially
    transform or filter them before transmission to clients.
    """

    @abstractmethod
    async def process(self, event: BaseEvent) -> AsyncGenerator[BaseEvent | None]:
        """Process an AGUI event and yield resulting events.

        Args:
            event: The AGUI event to process

        Yields:
            Processed BaseEvent objects

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseAGUIStateSnapshotHandler(metaclass=ABCMeta):
    """Abstract base class for AGUI state snapshot processing handlers.

    Defines the interface for handlers that process state snapshots and
    transform them as needed for different contexts or formats.
    """

    @abstractmethod
    async def process(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        """Process a state snapshot and return the transformed state.

        Args:
            state_snapshot: Dictionary containing the current state snapshot

        Returns:
            Transformed state snapshot dictionary

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseInOutHandler(metaclass=ABCMeta):
    """Abstract base class for handling input/output recording and transformation.

    Defines the interface for handlers that record incoming requests and outgoing responses,
    as well as potentially modify or transform output data before transmission.
    """

    @abstractmethod
    async def input_record(self, agui_input: RunAgentInput, request: Request) -> None:
        """Record incoming AGUI input for logging or audit purposes.

        Args:
            agui_input: The agent input data to record
            request: HTTP request containing client context

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    async def output_record(self, agui_event: dict[str, str]) -> None:
        """Record outgoing AGUI events for logging or audit purposes.

        Args:
            agui_event: Dictionary containing event data to record

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    async def output_catch_and_change(
        self, agui_event: dict[str, str]
    ) -> dict[str, str]:
        """Intercept and potentially modify outgoing AGUI events.

        Args:
            agui_event: Dictionary containing event data to potentially modify

        Returns:
            Modified event dictionary (may be unchanged)

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
