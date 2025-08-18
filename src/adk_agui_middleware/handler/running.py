from collections.abc import AsyncGenerator
from typing import Any

from ag_ui.core import BaseEvent, EventType, StateSnapshotEvent
from google.adk import Runner
from google.adk.agents import RunConfig
from google.adk.events import Event

from ..base_abc.event_handler import BaseEventHandler
from ..loggers.record_log import record_agui_raw_log, record_event_raw_log
from ..tools.event_translator import EventTranslator


class RunningHandler:
    def __init__(
        self,
        runner: Runner,
        run_config: RunConfig,
        adk_event_handler: None | BaseEventHandler = None,
        agui_event_handler: None | BaseEventHandler = None,
    ):
        self.runner: Runner = runner
        self.run_config: RunConfig = run_config
        self.adk_event_handler = (
            adk_event_handler
            if isinstance(adk_event_handler, BaseEventHandler)
            else None
        )
        self.agui_event_handler = (
            agui_event_handler
            if isinstance(agui_event_handler, BaseEventHandler)
            else None
        )
        self.event_translator = EventTranslator()
        self.is_long_running_tool = False

    @staticmethod
    async def _process_events_with_handler(
        event_stream: AsyncGenerator, log_func: Any, event_handler: Any | None
    ) -> AsyncGenerator:
        async for event in event_stream:
            log_func(event)
            if event_handler:
                async for new_event in event_handler.run_async(event):
                    yield new_event
            else:
                yield event

    async def _run_async_translator_adk_to_agui(
        self, adk_event: Event
    ) -> AsyncGenerator[BaseEvent]:
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
        return self.event_translator.force_close_streaming_message()

    def create_state_snapshot_event(
        self, final_state: dict[str, Any]
    ) -> StateSnapshotEvent:
        return self.event_translator.create_state_snapshot_event(final_state)

    def run_async_with_adk(
        self, *args: Any, **kwargs: Any
    ) -> AsyncGenerator[Event, None]:
        return self._process_events_with_handler(
            self.runner.run_async(*args, run_config=self.run_config, **kwargs),
            record_event_raw_log,
            self.adk_event_handler,
        )

    def run_async_with_agui(self, adk_event: Event) -> AsyncGenerator[BaseEvent]:
        return self._process_events_with_handler(
            self._run_async_translator_adk_to_agui(adk_event),
            record_agui_raw_log,
            self.agui_event_handler,
        )
