"""Abstract base classes for event and state handlers in the middleware."""

from abc import ABCMeta, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from ag_ui.core import BaseEvent
from google.adk.events import Event

from ..data_model.event import TranslateEvent
from ..tools.event_translator import EventTranslator


class BaseTranslateHandler(metaclass=ABCMeta):
    """Abstract base class for event translation handlers.

    Handles translation of ADK events to AGUI events using the provided event translator.
    """

    def __init__(self, event_translator: EventTranslator):
        """Initialize the translate handler with an event translator.

        Args:
            event_translator: Service for translating between event formats
        """
        self.event_translator = event_translator

    @abstractmethod
    def translate(self, adk_event: Event) -> AsyncGenerator[TranslateEvent]:
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
    async def process(self, event: Event) -> AsyncGenerator[Event]:
        """Process an ADK event and yield resulting events.

        Args:
            event: The ADK event to process

        Yields:
            Processed Event objects

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
    async def process(self, event: BaseEvent) -> AsyncGenerator[BaseEvent]:
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
