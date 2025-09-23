# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
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

from ..event.error_event import AGUIErrorEvent
from ..loggers.record_log import record_log
from .running import RunningHandler
from .session import SessionHandler
from .user_message import UserMessageHandler


class AGUIUserHandler:
    """Orchestrates user interactions with the agent through the AGUI interface.

    Manages the complete workflow of agent execution including session management,
    event translation, tool call tracking, and error handling. This handler is
    the primary coordinator for HITL (Human-in-the-Loop) workflows, managing
    the transition between agent execution and human intervention states.

    Key Responsibilities:
    - Orchestrates agent execution through the running handler
    - Manages session state and HITL workflow transitions
    - Tracks tool calls and manages pending tool call states
    - Coordinates between user messages, agent responses, and tool results
    """

    def __init__(
        self,
        running_handler: RunningHandler,
        user_message_handler: UserMessageHandler,
        session_handler: SessionHandler,
    ):
        """Initialize the AGUI user handler.

        Sets up the handler with its dependent components for managing the complete
        agent interaction workflow including execution, message processing, and
        session state management.

        Args:
            :param running_handler: Handler for executing agent runs and event translation
            :param user_message_handler: Handler for processing user messages and tool results
            :param session_handler: Handler for session state management and HITL workflows
        """
        self.running_handler = running_handler
        self.user_message_handler = user_message_handler
        self.session_handler = session_handler

        self.tool_call_ids: list[str] = []

    async def _async_init(self) -> None:
        """Initialize asynchronous components of the handler.

        Performs async initialization that cannot be done in __init__, specifically
        setting up long-running tool IDs from pending tool calls in session state.
        This is crucial for resuming HITL workflows correctly.
        """
        await self._initialize_long_running_tools()

    async def _initialize_long_running_tools(self) -> None:
        """Initialize long-running tool IDs from session state.

        Retrieves pending tool calls from session state and configures the running
        handler to properly handle these long-running operations. This ensures that
        tool calls marked as pending in previous requests are handled correctly
        in the current execution context.
        """
        self.running_handler.set_long_running_tool_ids(
            await self.session_handler.get_pending_tool_calls()
        )

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
        return self.user_message_handler.agui_content.run_id

    def call_start(self) -> RunStartedEvent:
        """Create a run started event.

        Creates a standardized run started event with the current session context.
        This event is sent to clients to indicate the beginning of agent processing.

        Returns:
            RunStartedEvent indicating the beginning of agent execution
        """
        return RunStartedEvent(
            type=EventType.RUN_STARTED, thread_id=self.session_id, run_id=self.run_id
        )

    def call_finished(self) -> RunFinishedEvent:
        """Create a run finished event.

        Creates a standardized run finished event with the current session context.
        This event is sent to clients to indicate the completion of agent processing.

        Returns:
            RunFinishedEvent indicating the completion of agent execution
        """
        return RunFinishedEvent(
            type=EventType.RUN_FINISHED, thread_id=self.session_id, run_id=self.run_id
        )

    def check_tools_event(self, event: BaseEvent) -> None:
        """Track tool call events for pending tool call management.

        Monitors agent events to track tool call lifecycle, adding tool call IDs
        to the tracking list when tools are invoked and removing them when tool
        results are processed. This is essential for HITL workflow management.

        Args:
            :param event: AGUI BaseEvent to check for tool call information
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

        This method completes the HITL (Human-in-the-Loop) workflow by processing
        human-provided tool results and removing the corresponding pending tool calls
        from session state. This allows the agent execution to resume with the
        human-provided input.

        HITL Completion Flow:
        1. Human provides tool results via API (tool result submission)
        2. This method extracts tool results from the user message
        3. Removes corresponding tool_call_ids from pending_tool_calls in session
        4. Agent execution resumes with the human-provided tool results
        5. Workflow continues with human input incorporated

        Returns:
            RunErrorEvent if no tool results found or processing fails, None on success

        Note:
            This is the critical completion step in HITL workflows, transforming
            pending human interventions back into active agent execution flow.
        """
        tool_results = await self.user_message_handler.extract_tool_results()
        if not tool_results:
            return AGUIErrorEvent.create_no_tool_results_error(
                self.user_message_handler.thread_id
            )
        try:
            for tool_result in tool_results:
                await self.session_handler.check_and_remove_pending_tool_call(
                    [tool_result["message"].tool_call_id]
                )
            record_log(
                f"Starting new execution for tool result in thread {self.session_id}"
            )
        except Exception as e:
            return AGUIErrorEvent.create_tool_processing_error_event(e)
        return None

    async def _run_async(self) -> AsyncGenerator[BaseEvent]:
        """Execute the agent asynchronously and yield translated events.

        Runs the agent with the user message, translates ADK events to AGUI events,
        tracks tool calls, handles long-running tools early return, forces streaming
        message closure, and creates final state snapshot if available.

        This method implements the core agent execution loop with proper event
        translation, tool call tracking, and state management.

        Yields:
            AGUI BaseEvent objects from agent execution and state management
        """
        async for adk_event in self.running_handler.run_async_with_adk(
            user_id=self.user_id,
            session_id=self.session_id,
            new_message=await self.user_message_handler.get_message(),
        ):
            async for agui_event in self.running_handler.run_async_with_agui(adk_event):
                yield agui_event
                self.check_tools_event(agui_event)
        if self.running_handler.is_long_running_tool:
            return
        async for ag_ui_event in self.running_handler.force_close_streaming_message():
            yield ag_ui_event
        final_state = await self.session_handler.get_session_state()
        if (
            event_final_state := await self.running_handler.create_state_snapshot_event(
                final_state
            )
        ) is not None:
            yield event_final_state

    async def _run_workflow(self) -> AsyncGenerator[BaseEvent]:
        """Execute the complete agent workflow with session management.

        Manages the entire workflow including session creation, state updates,
        agent execution, pending tool call management, and run completion.
        This orchestrates the full lifecycle of an agent execution request.

        Yields:
            AGUI BaseEvent objects for the complete workflow
        """
        yield self.call_start()
        await self.session_handler.check_and_create_session(
            self.user_message_handler.initial_state
        )
        await self.session_handler.update_session_state(
            self.user_message_handler.initial_state
        )
        async for event in self._run_async():
            yield event
        # Add any uncompleted tool calls to pending state for HITL workflow
        await self.session_handler.add_pending_tool_call(self.tool_call_ids)
        yield self.call_finished()

    async def run(self) -> AsyncGenerator[BaseEvent]:
        """Main entry point for running the AGUI user handler.

        Orchestrates the complete HITL (Human-in-the-Loop) workflow by determining
        if the incoming request is completing a previous HITL interaction (tool result
        submission) or starting a new agent execution. Manages the transition between
        HITL states and agent execution flow.

        HITL Workflow Logic:
        1. Check if request contains tool results (HITL completion)
        2. If tool results: Remove pending tool calls and resume execution
        3. If new request: Execute agent and add any tool calls to pending state
        4. Handle errors and state transitions throughout the process

        Yields:
            AGUI BaseEvent objects from the handler execution, including HITL state changes

        Note:
            This is the primary entry point for HITL workflow management, handling
            both initiation and completion of human intervention cycles.
        """
        await self._async_init()
        if self.user_message_handler.is_tool_result_submission and (
            error := await self.remove_pending_tool_call()
        ):
            yield error
            return
        try:
            async for event in self._run_workflow():
                yield event
        except Exception as e:
            yield AGUIErrorEvent.create_execution_error_event(e)
