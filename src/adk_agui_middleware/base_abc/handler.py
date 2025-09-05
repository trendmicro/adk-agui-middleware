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

    Defines the interface for custom event translation handlers that can
    modify or extend the default ADK to AGUI event translation behavior.
    Implementations can provide custom translation logic, filtering,
    or transformation of events during the translation pipeline.
    """

    @abstractmethod
    async def translate(self, adk_event: Event) -> AsyncGenerator[TranslateEvent]:
        """Translate an ADK event to AGUI event format.

        Transforms ADK events into AGUI format while providing control
        over the translation process through TranslateEvent flags.
        Implementations can yield multiple events or modify translation behavior.

        :param adk_event: The ADK event to be translated
        :yields: TranslateEvent objects containing translated AGUI events and control flags
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseADKEventHandler(metaclass=ABCMeta):
    """Abstract base class for ADK event processing handlers.

    Defines the interface for handlers that process ADK events and potentially
    transform or filter them before translation to AGUI format. This enables
    custom preprocessing of ADK events, including filtering, modification,
    or enrichment based on application-specific requirements.
    """

    @abstractmethod
    async def process(self, event: Event) -> AsyncGenerator[Event | None]:
        """Process an ADK event and yield resulting events.

        Processes the input ADK event and yields zero or more processed events.
        Can be used to filter events (yield nothing), transform events, or
        generate multiple events from a single input event.

        :param event: The ADK event to process
        :yields: Processed ADK Event objects, or None to filter out the event
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseADKEventTimeoutHandler(metaclass=ABCMeta):
    """Abstract base class for handling ADK event timeouts and fallback processing.

    Defines the interface for handlers that manage timeout behavior in event processing,
    including timeout duration configuration and fallback event generation when timeouts occur.
    This enables graceful handling of long-running or stuck agent processes.
    """

    @abstractmethod
    async def get_timeout(self) -> int:
        """Get the timeout duration in seconds for event processing.

        Defines how long the event processing should wait before triggering
        timeout fallback behavior. This allows dynamic timeout configuration
        based on context or processing requirements.

        :return: Timeout duration in seconds
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    async def process_timeout_fallback(self) -> AsyncGenerator[Event | None]:
        """Process timeout fallback and generate appropriate events.

        Called when event processing exceeds the configured timeout duration.
        Should generate fallback events to handle the timeout gracefully,
        such as error events, timeout notifications, or recovery actions.

        :yields: ADK Event objects to be processed as timeout fallback
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseAGUIEventHandler(metaclass=ABCMeta):
    """Abstract base class for AGUI event processing handlers.

    Defines the interface for handlers that process AGUI events and potentially
    transform or filter them before transmission to clients. This enables
    post-translation processing of AGUI events, including filtering based on
    client capabilities, enrichment with additional data, or format customization.
    """

    @abstractmethod
    async def process(self, event: BaseEvent) -> AsyncGenerator[BaseEvent | None]:
        """Process an AGUI event and yield resulting events.

        Processes the input AGUI event and yields zero or more processed events.
        Can be used to filter events (yield nothing), transform events for
        specific client requirements, or generate multiple events from a single input.

        :param event: The AGUI BaseEvent to process
        :yields: Processed AGUI BaseEvent objects, or None to filter out the event
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseAGUIStateSnapshotHandler(metaclass=ABCMeta):
    """Abstract base class for AGUI state snapshot processing handlers.

    Defines the interface for handlers that process state snapshots and
    transform them as needed for different contexts or formats. This enables
    customization of state data before it's returned to clients, including
    filtering sensitive data, reformatting for client consumption, or adding
    computed fields.
    """

    @abstractmethod
    async def process(self, state_snapshot: dict[str, Any]) -> dict[str, Any] | None:
        """Process a state snapshot and return the transformed state.

        Transforms the state snapshot for client consumption, potentially
        filtering sensitive data, adding computed fields, or reformatting
        the structure. Return None to suppress state snapshot transmission.

        :param state_snapshot: Dictionary containing the current session state snapshot
        :return: Transformed state snapshot dictionary, or None to suppress the snapshot
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class BaseInOutHandler(metaclass=ABCMeta):
    """Abstract base class for handling input/output recording and transformation.

    Defines the interface for handlers that record incoming requests and outgoing responses,
    as well as potentially modify or transform output data before transmission. This enables
    comprehensive audit logging, request/response transformation, and monitoring of all
    data flowing through the middleware.
    """

    @abstractmethod
    async def input_record(self, agui_input: RunAgentInput, request: Request) -> None:
        """Record incoming AGUI input for logging or audit purposes.

        Records incoming request data for audit trails, debugging, or analytics.
        Can be used to log user interactions, track API usage, or store request
        context for correlation with response data.

        :param agui_input: The agent input data to record
        :param request: HTTP request containing client context and headers
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    async def output_record(self, agui_event: dict[str, str]) -> None:
        """Record outgoing AGUI events for logging or audit purposes.

        Records outgoing response events for audit trails, debugging, or analytics.
        Can be used to track agent responses, monitor event patterns, or store
        interaction history for analysis.

        :param agui_event: Dictionary containing SSE-formatted event data to record
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    async def output_catch_and_change(
        self, agui_event: dict[str, str]
    ) -> dict[str, str]:
        """Intercept and potentially modify outgoing AGUI events.

        Provides the opportunity to transform or modify outgoing event data
        before transmission to clients. Can be used for data sanitization,
        format conversion, field addition/removal, or content filtering.

        :param agui_event: Dictionary containing SSE-formatted event data to potentially modify
        :return: Modified event dictionary (may be unchanged from input)
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
