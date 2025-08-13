"""Handler for managing AGUI user interactions and agent execution workflow."""

from collections.abc import AsyncGenerator

from ag_ui.core import (
    BaseEvent,
    EventType,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
)
from event.error_event import AGUIErrorEvent
from google.adk import Runner
from google.adk.agents import RunConfig
from google.adk.events import Event
from google.genai import types
from handler.session import SessionHandler
from handler.user_message import UserMessageHandler
from loggers.record_log import record_log
from tools.event_translator import EventTranslator


class AGUIUserHandler:
    """Orchestrates user interactions with the agent through the AGUI interface.

    Manages the complete workflow of agent execution including session management,
    event translation, tool call tracking, and error handling.
    """

    def __init__(
        self,
        runner: Runner,
        run_config: RunConfig,
        agui_message: UserMessageHandler,
        session_handler: SessionHandler,
    ):
        """Initialize the AGUI user handler.

        Args:
            runner: ADK Runner instance for agent execution
            run_config: Configuration for agent execution
            agui_message: Handler for processing user messages
            session_handler: Handler for session state management
        """
        self.runner = runner
        self.run_config = run_config
        self.user_message = agui_message
        self.session_handler = session_handler

        self.event_translator = EventTranslator()
        self.is_long_running_tool = False
        self.tool_call_ids = []

    @property
    def app_name(self) -> str:
        """Get the application name from the session handler.

        Returns:
            Application name string
        """
        return self.session_handler.app_name

    @property
    def user_id(self) -> str:
        """Get the user ID from the session handler.

        Returns:
            User identifier string
        """
        return self.session_handler.user_id

    @property
    def session_id(self) -> str:
        """Get the session ID from the session handler.

        Returns:
            Session identifier string
        """
        return self.session_handler.session_id

    @property
    def run_id(self) -> str:
        """Get the run ID from the user message content.

        Returns:
            Run identifier string
        """
        return self.user_message.agui_content.run_id

    def call_start(self) -> RunStartedEvent:
        """Create a run started event.

        Returns:
            RunStartedEvent indicating the beginning of agent execution
        """
        return RunStartedEvent(
            type=EventType.RUN_STARTED, thread_id=self.session_id, run_id=self.run_id
        )

    def call_finished(self) -> RunFinishedEvent:
        """Create a run finished event.

        Returns:
            RunFinishedEvent indicating the completion of agent execution
        """
        return RunFinishedEvent(
            type=EventType.RUN_FINISHED, thread_id=self.session_id, run_id=self.run_id
        )

    async def check_tools_event(self, event: BaseEvent) -> None:
        """Track tool call events for pending tool call management.

        Adds tool call IDs when tools are called and removes them when
        tool results are received.

        Args:
            event: Base event to check for tool call information
        """
        if isinstance(event, ToolCallEndEvent):
            self.tool_call_ids.append(event.tool_call_id)
        if (
            isinstance(event, ToolCallResultEvent)
            and event.tool_call_id in self.tool_call_ids
        ):
            self.tool_call_ids.remove(event.tool_call_id)

    async def remove_pending_tool_call(self) -> RunErrorEvent | None:
        """Remove pending tool calls from session state after processing tool results.

        Extracts tool results from the user message and removes corresponding
        pending tool calls from the session state.

        Returns:
            RunErrorEvent if tool result processing fails, None on success
        """
        tool_results = await self.user_message.extract_tool_results()
        if not tool_results:
            return AGUIErrorEvent.no_tool_results(self.user_message.thread_id)
        try:
            for tool_result in tool_results:
                await self.session_handler.check_and_remove_pending_tool_call(
                    tool_result["message"].tool_call_id
                )
            record_log(
                f"Starting new execution for tool result in thread {self.session_id}"
            )
        except Exception as e:
            return AGUIErrorEvent.tool_result_processing_error(e)

    async def _run_async_translator_adk_to_agui(
        self, adk_event: Event
    ) -> AsyncGenerator[BaseEvent]:
        """Translate ADK events to AGUI events with long-running tool support.

        Handles both regular event translation and long-running function calls,
        setting the long-running tool flag when appropriate.

        Args:
            adk_event: ADK event to translate

        Yields:
            AGUI BaseEvent objects translated from the ADK event
        """
        if not adk_event.is_final_response():
            async for ag_ui_event in self.event_translator.translate(adk_event):
                yield ag_ui_event
        else:
            async for ag_ui_event in self.event_translator.translate_lro_function_calls(
                adk_event
            ):
                yield ag_ui_event
                self.is_long_running_tool = ag_ui_event.type == EventType.TOOL_CALL_END

    async def _run_async_with_adk(
        self, message: types.Content
    ) -> AsyncGenerator[Event]:
        """Execute the agent with the given message using ADK runner.

        Args:
            message: Google GenAI Content object containing the user message

        Yields:
            ADK Event objects from agent execution
        """
        async for event in self.runner.run_async(
            user_id=self.user_id,
            session_id=self.session_id,
            new_message=message,
        ):
            yield event

    async def _run_async(self) -> AsyncGenerator[BaseEvent]:
        """Execute the agent asynchronously and yield translated events.

        Runs the agent with the user message, translates ADK events to AGUI events,
        and handles long-running tools, streaming message cleanup, and state snapshots.

        Yields:
            AGUI BaseEvent objects from agent execution
        """
        async for adk_event in self._run_async_with_adk(
            await self.user_message.get_message()
        ):
            async for agui_event in self._run_async_translator_adk_to_agui(adk_event):
                await self.check_tools_event(agui_event)
                yield agui_event
                if self.is_long_running_tool:
                    return
        async for ag_ui_event in self.event_translator.force_close_streaming_message():
            yield ag_ui_event
        if final_state := await self.session_handler.get_session_state():
            yield self.event_translator.create_state_snapshot_event(final_state)

    async def _run_workflow(self) -> AsyncGenerator[BaseEvent]:
        """Execute the complete agent workflow with session management.

        Manages the entire workflow including session creation, state updates,
        agent execution, pending tool call management, and run completion.

        Yields:
            AGUI BaseEvent objects for the complete workflow
        """
        yield self.call_start()
        await self.session_handler.check_and_create_session(
            self.user_message.initial_state
        )
        await self.session_handler.update_session_state(self.user_message.initial_state)
        async for event in self._run_async():
            yield event
        for tool_call_id in self.tool_call_ids:
            await self.session_handler.add_pending_tool_call(tool_call_id)
        yield self.call_finished()

    async def run(self) -> AsyncGenerator[BaseEvent]:
        """Main entry point for running the AGUI user handler.

        Handles tool result submissions by removing pending tool calls,
        then executes the complete workflow with error handling.

        Yields:
            AGUI BaseEvent objects from the handler execution
        """
        if self.user_message.is_tool_result_submission and (
            error := await self.remove_pending_tool_call()
        ):
            yield error
            return
        try:
            async for event in self._run_workflow():
                yield event
        except Exception as e:
            yield AGUIErrorEvent.execution_error(e)
