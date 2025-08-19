"""Handler for managing agent execution and event translation between ADK and AGUI formats."""

from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from ag_ui.core import BaseEvent, EventType, StateSnapshotEvent
from google.adk import Runner
from google.adk.agents import RunConfig
from google.adk.events import Event

from ..loggers.record_log import record_agui_raw_log, record_event_raw_log
from ..tools.event_translator import EventTranslator


class RunningHandler:
    """Manages agent execution and event translation between ADK and AGUI formats.
    
    Orchestrates the execution of ADK agents while translating their events into 
    AGUI-compatible format. Handles streaming messages, long-running tools, and 
    state snapshots with proper event processing pipelines.
    """
    def __init__(
        self,
        runner: Runner,
        run_config: RunConfig,
        adk_event_handler: Callable[[Event], AsyncGenerator[Event, None]] | None = None,
        agui_event_handler: Callable[[BaseEvent], AsyncGenerator[BaseEvent, None]]
        | None = None,
        agui_state_snapshot_handler: Callable[
            [dict[str, Any]], Awaitable[dict[str, Any]]
        ]
        | None = None,
    ):
        """Initialize the running handler with agent runner and configuration.
        
        Args:
            runner: ADK Runner instance for executing agent operations
            run_config: Configuration for agent run behavior and streaming mode
            adk_event_handler: Optional handler for processing ADK events before translation
            agui_event_handler: Optional handler for processing AGUI events after translation
            agui_state_snapshot_handler: Optional handler for processing state snapshots
        """
        self.runner: Runner = runner
        self.run_config: RunConfig = run_config
        self.adk_event_handler = adk_event_handler
        self.agui_event_handler = agui_event_handler
        self.agui_state_snapshot_handler = agui_state_snapshot_handler
        self.event_translator = EventTranslator()
        self.is_long_running_tool = False

    @staticmethod
    async def _process_events_with_handler(
        event_stream: AsyncGenerator,
        log_func: Any,
        event_handler: Callable[
            [Event | BaseEvent], AsyncGenerator[Event | BaseEvent, None]
        ]
        | None,
    ) -> AsyncGenerator:
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
        async for event in event_stream:
            log_func(event)
            if event_handler:
                async for new_event in event_handler(event):
                    yield new_event
            else:
                yield event

    async def _run_async_translator_adk_to_agui(
        self, adk_event: Event
    ) -> AsyncGenerator[BaseEvent]:
        """Translate ADK events to AGUI events with long-running tool detection.
        
        Handles standard event translation and detects long-running tools that 
        require special processing. Sets the long-running tool flag when detected.
        
        Args:
            adk_event: ADK event to translate
            
        Yields:
            AGUI BaseEvent objects translated from the ADK event
        """
        if not adk_event.is_final_response():
            async for agui_event in self.event_translator.translate(adk_event):
                yield agui_event
        else:
            async for agui_event in self.event_translator.translate_lro_function_calls(
                adk_event
            ):
                yield agui_event
                if adk_event.type == EventType.TOOL_CALL_END:
                    self.is_long_running_tool = True

    def force_close_streaming_message(self) -> AsyncGenerator[BaseEvent, None]:
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
            final_state = await self.agui_state_snapshot_handler(final_state)
        return self.event_translator.create_state_snapshot_event(final_state)

    def run_async_with_adk(
        self, *args: Any, **kwargs: Any
    ) -> AsyncGenerator[Event, None]:
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
