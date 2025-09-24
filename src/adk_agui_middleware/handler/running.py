# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Handler for managing agent execution and event translation between ADK and AGUI formats."""

import asyncio
from collections.abc import AsyncGenerator, Callable
from typing import Any

from ag_ui.core import BaseEvent, StateSnapshotEvent
from google.adk import Runner
from google.adk.agents import RunConfig
from google.adk.events import Event

from ..base_abc.handler import (
    BaseADKEventHandler,
    BaseADKEventTimeoutHandler,
    BaseAGUIEventHandler,
    BaseAGUIStateSnapshotHandler,
    BaseTranslateHandler,
)
from ..data_model.context import HandlerContext
from ..event.event_translator import EventTranslator
from ..loggers.record_log import (
    record_agui_raw_log,
    record_event_raw_log,
    record_warning_log,
)


class RunningHandler:
    """Manages agent execution and event translation between ADK and AGUI formats.

    Orchestrates the execution of ADK agents while translating their events into
    AGUI-compatible format. Handles streaming messages, long-running tools, and
    state snapshots with proper event processing pipelines.

    Key Responsibilities:
    - Execute ADK agents with proper configuration
    - Translate ADK events to AGUI format through event translator
    - Manage custom event handlers for preprocessing and postprocessing
    - Handle timeout scenarios and fallback processing
    - Detect and manage long-running tool executions
    - Generate state snapshot events for session persistence
    """

    def __init__(
        self,
        runner: Runner | None = None,
        run_config: RunConfig | None = None,
        handler_context: HandlerContext | None = None,
    ):
        """Initialize the running handler with agent runner and configuration.

        Sets up the handler with the necessary components for agent execution
        and event processing, including optional custom handlers for extending
        the default processing pipeline.

        Args:
            :param runner: ADK Runner instance for executing agent operations
            :param run_config: Configuration for agent run behavior and streaming mode
            :param handler_context: Context containing optional event handlers for processing
        """
        self.runner: Runner | None = runner
        self.run_config: RunConfig | None = run_config
        self.event_translator = EventTranslator()

        self.adk_event_handler: BaseADKEventHandler | None = None
        self.adk_event_timeout_handler: BaseADKEventTimeoutHandler | None = None
        self.agui_event_handler: BaseAGUIEventHandler | None = None
        self.agui_state_snapshot_handler: BaseAGUIStateSnapshotHandler | None = None
        self.translate_handler: BaseTranslateHandler | None = None
        self._init_handler(handler_context)

    def _init_handler(self, handler_context: HandlerContext | None) -> None:
        """Initialize optional event handlers from the provided context.

        Creates instances of event handlers if they are configured in the handler context.
        Each handler type serves a specific purpose in the event processing pipeline,
        enabling customization of event processing behavior.

        Args:
            :param handler_context: Context containing handler class types to instantiate
        """
        if handler_context is None:
            return
        for attr in [
            "adk_event_handler",
            "adk_event_timeout_handler",
            "agui_event_handler",
            "agui_state_snapshot_handler",
            "translate_handler",
        ]:
            if handler_class := getattr(handler_context, attr, None):
                setattr(self, attr, handler_class())

    async def _get_timeout(self, enable_timeout: bool) -> float | None:
        """Get timeout duration for event processing if timeout is enabled.

        Retrieves the timeout configuration from the timeout handler if available
        and timeout is enabled, otherwise returns None to disable timeout handling.

        Args:
            :param enable_timeout: Whether timeout handling is enabled for this operation

        Returns:
            Timeout duration in seconds, or None if timeout is disabled
        """
        if not (self.adk_event_timeout_handler and enable_timeout):
            return None
        return await self.adk_event_timeout_handler.get_timeout()

    async def _handle_timeout_fallback(self) -> AsyncGenerator[Event | None, Any]:
        """Handle timeout fallback when event processing exceeds time limit.

        Delegates to the timeout handler to generate appropriate fallback events
        when agent processing exceeds the configured timeout duration.

        Yields:
            Fallback ADK events to process when timeout occurs, or None if no handler
        """
        if self.adk_event_timeout_handler is None:
            return
        async for (
            event
        ) in await self.adk_event_timeout_handler.process_timeout_fallback():
            yield event

    @staticmethod
    async def _process_single_event(
        event: BaseEvent | Event,
        log_func: Any,
        event_handler: BaseADKEventHandler | BaseAGUIEventHandler | None,
    ) -> AsyncGenerator[BaseEvent | Event]:
        """Process a single event with logging and optional custom event handler.

        Logs the event and optionally processes it through a custom handler.
        User-authored events are passed through unchanged to avoid infinite loops.

        Args:
            :param event: Event to process (ADK or AGUI format)
            :param log_func: Logging function to record the event
            :param event_handler: Optional custom handler to process the event

        Yields:
            Processed events (original or modified by handler)
        """
        log_func(event)
        if not event_handler or (isinstance(event, Event) and event.author == "user"):
            yield event
            return
        async for new_event in await event_handler.process(event):  # type: ignore[arg-type]
            if new_event:
                yield new_event

    async def _process_events_with_handler(
        self,
        event_stream: AsyncGenerator,  # type: ignore[type-arg]
        log_func: Any,
        event_handler: BaseADKEventHandler | BaseAGUIEventHandler | None = None,
        enable_timeout: bool = False,
    ) -> AsyncGenerator:  # type: ignore[type-arg]
        """Process an event stream with optional event handler and logging.

        Applies logging to all events and optionally processes them through
        a custom event handler before yielding them.

        Args:
            :param event_stream: Async generator of events to process
            :param log_func: Function to call for logging each event
            :param event_handler: Optional handler to process events before yielding
            :param enable_timeout: Whether to enable timeout handling for ADK events

        Yields:
            Events from the stream, potentially modified by the event handler
        """
        try:
            async with asyncio.timeout(await self._get_timeout(enable_timeout)):
                async for event in event_stream:
                    async for processed_event in self._process_single_event(
                        event, log_func, event_handler
                    ):
                        yield processed_event
        except TimeoutError:
            record_warning_log("Timeout occurred while processing events.")
            async for fallback_event in self._handle_timeout_fallback():
                yield fallback_event

    def _select_translation_function(
        self, adk_event: Event
    ) -> Callable[[Event], AsyncGenerator[BaseEvent]]:
        """Select appropriate translation function based on event characteristics.

        Determines whether to use standard translation or long-running function
        call translation based on event content and completion status. This
        enables proper handling of different event types in the translation pipeline.

        Args:
            :param adk_event: ADK event to analyze for translation method selection

        Returns:
            Translation function appropriate for the event type
        """

        if adk_event.is_final_response() and adk_event.long_running_tool_ids:
            return self.event_translator.translate_long_running_function_calls
        return self.event_translator.translate

    async def _translate_adk_to_agui_async(
        self, adk_event: Event
    ) -> AsyncGenerator[BaseEvent]:
        """Translate ADK events to AGUI events with custom handler and long-running tool detection.

        Uses custom translate handler if available, otherwise delegates to event translator.
        Handles retune logic and selects appropriate translation function based on
        whether the event is a final response. Detects long-running tools throughout.

        Args:
            :param adk_event: ADK event to translate

        Yields:
            AGUI BaseEvent objects translated from the ADK event
        """
        if self.translate_handler:
            async for translate_event in await self.translate_handler.translate(
                adk_event
            ):
                if translate_event.agui_event is not None:
                    yield translate_event.agui_event
                if translate_event.is_retune:
                    return
                if translate_event.adk_event and translate_event.is_replace:
                    adk_event = translate_event.adk_event

        translate_func = self._select_translation_function(adk_event)
        async for agui_event in translate_func(adk_event):
            yield agui_event

    def set_long_running_tool_ids(self, long_running_tool_ids: dict[str, str]) -> None:
        """Set long-running tool IDs in the event translator.

        Configures the event translator with the list of tool call IDs that are
        marked as long-running operations, enabling proper handling of these tools
        during event translation. This is essential for HITL workflow management.

        Args:
            :param long_running_tool_ids: List of tool call IDs for long-running operations
        """
        self.event_translator.long_running_tool_ids = long_running_tool_ids

    def force_close_streaming_message(self) -> AsyncGenerator[BaseEvent]:
        """Force close any active streaming message in the event translator.

        Delegates to the event translator to handle cleanup of unclosed
        streaming messages that may remain after agent execution. This ensures
        proper message closure for incomplete streaming responses.

        Returns:
            AsyncGenerator yielding events for closing streaming messages
        """
        return self.event_translator.force_close_streaming_message()

    async def create_state_snapshot_event(
        self, final_state: dict[str, Any]
    ) -> StateSnapshotEvent | None:
        """Create a state snapshot event with optional state processing.

        Processes the final state through the configured state snapshot handler
        if available, then creates a state snapshot event. This enables custom
        state processing before sending the snapshot to clients.

        Args:
            :param final_state: Dictionary containing the final session state

        Returns:
            StateSnapshotEvent containing the processed state, or None if suppressed
        """
        if self.agui_state_snapshot_handler is not None:
            final_state = await self.agui_state_snapshot_handler.process(final_state)  # type: ignore[assignment]
        return (
            None
            if final_state is None
            else self.event_translator.create_state_snapshot_event(final_state)
        )

    def run_async_with_adk(self, *args: Any, **kwargs: Any) -> AsyncGenerator[Event]:
        """Execute agent with ADK and process events through ADK event handler.

        Runs the ADK agent asynchronously with the provided arguments and
        processes the resulting events through the configured ADK event handler.
        This is the primary method for executing agents and obtaining event streams.

        Args:
            :param *args: Positional arguments to pass to the runner (typically user_id, session_id, message)
            :param **kwargs: Keyword arguments to pass to the runner

        Returns:
            AsyncGenerator yielding processed ADK Event objects

        Raises:
            ValueError: If runner or run_config is not provided
        """
        if not self.runner or not self.run_config:
            raise ValueError("Runner and RunConfig must be provided to run the agent.")
        return self._process_events_with_handler(
            self.runner.run_async(*args, run_config=self.run_config, **kwargs),
            record_event_raw_log,
            self.adk_event_handler,
            enable_timeout=True,
        )

    def run_async_with_history(
        self, runner: AsyncGenerator[Event]
    ) -> AsyncGenerator[Event]:
        """Process historical events through the ADK event handler pipeline.

        Takes a pre-generated stream of ADK events (e.g., from conversation history)
        and processes them through the configured ADK event handler without timeout.
        This is typically used for replaying or reprocessing stored events during
        conversation reconstruction or analysis.

        Args:
            :param runner: AsyncGenerator yielding ADK Event objects to process

        Returns:
            AsyncGenerator yielding processed ADK Event objects
        """
        return self._process_events_with_handler(
            runner,
            record_event_raw_log,
            self.adk_event_handler,
        )

    def run_async_with_agui(self, adk_event: Event) -> AsyncGenerator[BaseEvent]:
        """Translate ADK event to AGUI events and process through AGUI event handler.

        Takes an ADK event, translates it to AGUI format using the event translator,
        and processes the resulting events through the configured AGUI event handler.
        This is the core method for converting ADK events to client-ready AGUI events.

        Args:
            :param adk_event: ADK Event to translate and process

        Returns:
            AsyncGenerator yielding processed AGUI BaseEvent objects
        """
        return self._process_events_with_handler(
            self._translate_adk_to_agui_async(adk_event),
            record_agui_raw_log,
            self.agui_event_handler,
        )
