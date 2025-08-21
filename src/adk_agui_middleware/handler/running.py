"""Handler for managing agent execution and event translation between ADK and AGUI formats."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from ag_ui.core import BaseEvent, EventType, StateSnapshotEvent
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
from ..loggers.record_log import (
    record_agui_raw_log,
    record_event_raw_log,
    record_warning_log,
)
from ..tools.event_translator import EventTranslator


class RunningHandler:
    """Manages agent execution and event translation between ADK and AGUI formats.

    Orchestrates the execution of ADK agents while translating their events into
    AGUI-compatible format. Handles streaming messages, long-running tools, and
    state snapshots with proper event processing pipelines.
    """

    def __init__(
            self, runner: Runner, run_config: RunConfig, handler_context: HandlerContext
    ):
        """Initialize the running handler with agent runner and configuration.

        Args:
            runner: ADK Runner instance for executing agent operations
            run_config: Configuration for agent run behavior and streaming mode
            handler_context: Context containing optional event handlers for processing
        """
        self.runner: Runner = runner
        self.run_config: RunConfig = run_config
        self.event_translator = EventTranslator()
        self.is_long_running_tool = False

        self.adk_event_handler: BaseADKEventHandler | None = None
        self.adk_event_timeout_handler: BaseADKEventTimeoutHandler | None = None
        self.agui_event_handler: BaseAGUIEventHandler | None = None
        self.agui_state_snapshot_handler: BaseAGUIStateSnapshotHandler | None = None
        self.translate_handler: BaseTranslateHandler | None = None
        self._init_handler(handler_context)

    def _init_handler(self, handler_context: HandlerContext) -> None:
        if handler_context.adk_event_handler:
            self.adk_event_handler = handler_context.adk_event_handler()
        if handler_context.adk_event_timeout_handler:
            self.adk_event_timeout_handler = handler_context.adk_event_timeout_handler()
        if handler_context.agui_event_handler:
            self.agui_event_handler = handler_context.agui_event_handler()
        if handler_context.agui_state_snapshot_handler:
            self.agui_state_snapshot_handler = (
                handler_context.agui_state_snapshot_handler()
            )
        if handler_context.translate_handler:
            self.translate_handler = handler_context.translate_handler()

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
            event_stream: Async generator of events to process
            log_func: Function to call for logging each event
            event_handler: Optional handler to process events before yielding

        Yields:
            Events from the stream, potentially modified by the event handler
        """
        timeout = (
            await self.adk_event_timeout_handler.get_timeout()
            if self.adk_event_timeout_handler and enable_timeout
            else None
        )
        try:
            async with asyncio.timeout(timeout):
                async for event in event_stream:
                    log_func(event)
                    if event_handler:
                        async for new_event in await event_handler.process(event):
                            yield new_event
                    else:
                        yield event
        except TimeoutError:
            record_warning_log("Timeout occurred while processing events.")
            if self.adk_event_timeout_handler is None:
                return
            async for (
                    new_event
            ) in await self.adk_event_timeout_handler.process_timeout_fallback():
                yield new_event

    def _check_is_long_tool(self, adk_event: Event, agui_event: BaseEvent) -> None:
        """Check if the event indicates a long-running tool and set flag accordingly.

        Args:
            adk_event: ADK event to check for long-running tool indicators
        """
        if adk_event.is_final_response() and agui_event.type == EventType.TOOL_CALL_END:
            self.is_long_running_tool = True

    async def _run_async_translator_adk_to_agui(
            self, adk_event: Event
    ) -> AsyncGenerator[BaseEvent]:
        """Translate ADK events to AGUI events with custom handler and long-running tool detection.

        Uses custom translate handler if available, otherwise delegates to event translator.
        Handles retune logic and selects appropriate translation function based on
        whether the event is a final response. Detects long-running tools throughout.

        Args:
            adk_event: ADK event to translate

        Yields:
            AGUI BaseEvent objects translated from the ADK event
        """
        if self.translate_handler:
            async for translate_event in await self.translate_handler.translate(
                    adk_event
            ):
                if translate_event.agui_event is not None:
                    yield translate_event.agui_event
                    self._check_is_long_tool(adk_event, translate_event.agui_event)
                if translate_event.is_retune:
                    return

        has_content = adk_event.content and adk_event.content.parts
        is_incomplete_response = not adk_event.is_final_response()
        has_content_without_metadata = not adk_event.usage_metadata and has_content

        if is_incomplete_response or has_content_without_metadata:
            func = self.event_translator.translate
        else:
            func = self.event_translator.translate_lro_function_calls

        async for agui_event in func(adk_event):
            yield agui_event
            self._check_is_long_tool(adk_event, agui_event)

    def force_close_streaming_message(self) -> AsyncGenerator[BaseEvent]:
        """Force close any active streaming message in the event translator.

        Delegates to the event translator to handle cleanup of unclosed
        streaming messages that may remain after agent execution.

        Returns:
            AsyncGenerator yielding events for closing streaming messages
        """
        return self.event_translator.force_close_streaming_message()

    async def create_state_snapshot_event(
            self, final_state: dict[str, Any]
    ) -> StateSnapshotEvent:
        """Create a state snapshot event with optional state processing.

        Processes the final state through the configured state snapshot handler
        if available, then creates a state snapshot event.

        Args:
            final_state: Dictionary containing the final session state

        Returns:
            StateSnapshotEvent containing the processed state
        """
        if self.agui_state_snapshot_handler is not None:
            final_state = await self.agui_state_snapshot_handler.process(final_state)
        return self.event_translator.create_state_snapshot_event(final_state)

    def run_async_with_adk(self, *args: Any, **kwargs: Any) -> AsyncGenerator[Event]:
        """Execute agent with ADK and process events through ADK event handler.

        Runs the ADK agent asynchronously with the provided arguments and
        processes the resulting events through the configured ADK event handler.

        Args:
            *args: Positional arguments to pass to the runner
            **kwargs: Keyword arguments to pass to the runner

        Returns:
            AsyncGenerator yielding processed ADK Event objects
        """
        return self._process_events_with_handler(
            self.runner.run_async(*args, run_config=self.run_config, **kwargs),
            record_event_raw_log,
            self.adk_event_handler,
            enable_timeout=True,
        )

    def run_async_with_agui(self, adk_event: Event) -> AsyncGenerator[BaseEvent]:
        """Translate ADK event to AGUI events and process through AGUI event handler.

        Takes an ADK event, translates it to AGUI format, and processes the
        resulting events through the configured AGUI event handler.

        Args:
            adk_event: ADK Event to translate and process

        Returns:
            AsyncGenerator yielding processed AGUI BaseEvent objects
        """
        return self._process_events_with_handler(
            self._run_async_translator_adk_to_agui(adk_event),
            record_agui_raw_log,
            self.agui_event_handler,
        )
