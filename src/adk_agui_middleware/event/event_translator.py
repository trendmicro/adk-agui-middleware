# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Event translation service for converting ADK events to AGUI format with streaming support."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from ag_ui.core import (
    BaseEvent,
    CustomEvent,
    EventType,
    StateDeltaEvent,
    StateSnapshotEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from google.adk.events import Event as ADKEvent

from ..loggers.record_log import record_debug_log, record_error_log, record_warning_log
from ..utils.translate import FunctionCallEventUtil, MessageEventUtil, StateEventUtil


class EventTranslator:
    """Translates events between ADK (Agent Development Kit) and AGUI formats.

    Handles the complex conversion of ADK events to AGUI events, managing streaming
    messages, tool calls, function calls, and state updates. Maintains internal state
    for streaming operations and long-running tool executions.

    Key Responsibilities:
    - Convert ADK events to AGUI-compatible format
    - Manage streaming message state and sequencing
    - Handle tool call and function response translation
    - Process state deltas and custom metadata
    - Support long-running tool detection and management
    """

    def __init__(
        self, retune_on_stream_complete: bool = False, add_raw_event: bool = False
    ) -> None:
        """Initialize the event translator with empty state containers.

        Sets up internal state tracking for streaming messages, long-running tools,
        and utility classes for different types of event translation.
        """
        self.retune_on_stream_complete = retune_on_stream_complete
        self.add_raw_event = add_raw_event
        self._streaming_message_id: dict[str, str] = {}
        self.long_running_tool_ids: dict[str, str] = {}  # IDs of long-running tools
        self.state_event_util = StateEventUtil()
        self.function_call_event_util = FunctionCallEventUtil()
        self.message_event_util = MessageEventUtil()

    def _add_adk_event(self, raw_event: ADKEvent | None) -> ADKEvent | None:
        """Optionally attach the original ADK event to emitted AGUI events.

        When ``self.add_raw_event`` is enabled, downstream AGUI events include a
        reference to the originating ADK event for debugging and tracing.

        Args:
            :param raw_event: The originating ADK event to optionally attach

        Returns:
            The ADK event if attachment is enabled; otherwise ``None``
        """
        return raw_event if self.add_raw_event else None

    async def translate(self, adk_event: ADKEvent) -> AsyncGenerator[BaseEvent]:
        """Translate an ADK event into corresponding AGUI events.

        Processes different types of ADK events (text content, function calls,
        function responses, state updates) and yields appropriate AGUI events.
        This is the main entry point for event translation in the middleware.

        Args:
            :param adk_event: ADK event to translate

        Yields:
            BaseEvent objects in AGUI format
        """
        try:
            # Skip user-authored events as they don't need translation
            if adk_event.author == "user":
                return
            # Handle text content streaming
            if adk_event.content and adk_event.content.parts:
                async for event in self.translate_text_content(adk_event):
                    yield event
            # Handle function calls with proper streaming closure
            if adk_event.get_function_calls():
                async for event in self._handle_function_calls(adk_event):
                    yield event
            # Handle function responses from tool execution
            if adk_event.get_function_responses():
                async for event in self.translate_function_responses(adk_event):
                    yield event
            # Handle state updates and custom metadata
            async for event in self._handle_additional_data(adk_event):
                yield event
        except Exception as e:
            record_error_log("Error translating ADK event.", e)

    async def _handle_function_calls(
        self, adk_event: ADKEvent
    ) -> AsyncGenerator[BaseEvent]:
        """Handle function calls by closing streaming messages and translating calls.

        Ensures proper sequencing by closing any active streaming messages before
        processing tool calls, then translates the function calls to AGUI events.

        Args:
            :param adk_event: ADK event containing function calls

        Yields:
            BaseEvent objects for function call handling
        """
        # Force close any active streaming message before handling function calls
        async for event in self.force_close_streaming_message():
            yield event
        # Translate the function calls to AGUI events
        async for event in self.function_call_event_util.generate_function_calls_event(
            adk_event.get_function_calls(), self._add_adk_event(adk_event)
        ):
            yield event

    async def _handle_additional_data(
        self, adk_event: ADKEvent
    ) -> AsyncGenerator[BaseEvent]:
        """Handle additional data like state deltas and custom metadata.

        Processes auxiliary data from ADK events including state updates
        and custom metadata, converting them to appropriate AGUI events.

        Args:
            :param adk_event: ADK event potentially containing additional data

        Yields:
            BaseEvent objects for state updates and custom events
        """
        # Handle state delta updates
        if adk_event.actions and adk_event.actions.state_delta:
            yield self.create_state_delta_event(
                adk_event.actions.state_delta, adk_event=self._add_adk_event(adk_event)
            )
        # Handle custom metadata as custom events
        if adk_event.custom_metadata:
            yield CustomEvent(
                type=EventType.CUSTOM,
                name="adk_custom_metadata",
                value=adk_event.custom_metadata,
                raw_event=self._add_adk_event(adk_event),
            )

    async def translate_text_content(
        self, adk_event: ADKEvent
    ) -> AsyncGenerator[BaseEvent]:
        """Translate text content from ADK event to AGUI streaming text events.

        Handles streaming text messages by managing message start, content chunks,
        and message end events. Tracks streaming state to ensure proper event sequencing
        and supports both streaming and non-streaming text responses.

        Args:
            :param adk_event: ADK event containing text content to translate

        Yields:
            AGUI text message events (start, content, end) for streaming text
        """
        if not (adk_event.content and adk_event.content.parts):
            return
        text_parts = [part.text for part in adk_event.content.parts if part.text]
        if not text_parts:
            return
        author_id = self._streaming_message_id.get(adk_event.author, None)
        add_adk_event = self._add_adk_event(adk_event)

        if not author_id and adk_event.is_final_response() and not adk_event.partial:
            async for agui_event in self.message_event_util.generate_message_event(
                adk_event.id, "".join(text_parts), adk_event=add_adk_event
            ):
                yield agui_event
            return

        # Start streaming if not already streaming and not a final response
        if not author_id and not adk_event.is_final_response():
            author_id = str(uuid.uuid4())
            self._streaming_message_id[adk_event.author] = author_id
            yield TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=author_id,
                role="assistant",
                raw_event=add_adk_event,
            )

        # Yield content if there's text and we're streaming
        if (
            author_id
            and (combined_text := "".join(text_parts))
            and not (
                adk_event.is_final_response() and not self.retune_on_stream_complete
            )
        ):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=author_id,
                delta=combined_text,
                raw_event=add_adk_event,
            )

        # End streaming on final response
        if author_id and adk_event.is_final_response():
            yield TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=author_id,
                raw_event=add_adk_event,
            )
            del self._streaming_message_id[adk_event.author]

    async def translate_long_running_function_calls(
        self, adk_event: ADKEvent
    ) -> AsyncGenerator[BaseEvent]:
        """Translate long-running operation (LRO) function calls to AGUI tool events.

        Processes function calls that are marked as long-running operations and
        generates appropriate AGUI tool call events without waiting for completion.

        Args:
            :param adk_event: ADK event containing long-running function calls

        Yields:
            AGUI tool call events for long-running operations
        """
        if not (adk_event.content and adk_event.content.parts):
            return
        for part in adk_event.content.parts:
            if (
                (not part.function_call)
                or part.function_call.id is None
                or part.function_call.name is None
                or part.function_call.id not in (adk_event.long_running_tool_ids or [])
            ):
                continue
            self.long_running_tool_ids[part.function_call.id] = part.function_call.name
            async for (
                agui_event
            ) in self.function_call_event_util.generate_function_call_event(
                part.function_call.id,
                part.function_call.name,
                part.function_call.args,
                adk_event=self._add_adk_event(adk_event),
            ):
                yield agui_event

    async def translate_function_responses(
        self, adk_event: ADKEvent
    ) -> AsyncGenerator[BaseEvent]:
        """Translate function responses to AGUI tool call result events.

        Processes function execution responses and generates AGUI ToolCallResultEvent
        objects for non-long-running tools. Long-running tool results are skipped
        as they are handled separately in the HITL workflow.

        Args:
            :param adk_event: ADK event containing one or more function responses
        Yields:
            AGUI ToolCallResultEvent objects for completed function calls
        """
        for func_response in adk_event.get_function_responses():
            tool_call_id = func_response.id or str(uuid.uuid4())
            if not self.long_running_tool_ids.get(tool_call_id):
                yield self.function_call_event_util.create_function_result_event(
                    tool_call_id=tool_call_id,
                    content=func_response.response,
                    adk_event=self._add_adk_event(adk_event),
                )
            else:
                record_debug_log(
                    f"Skipping ToolCallResultEvent for long-running tool: {tool_call_id}"
                )

    def create_state_delta_event(
        self, state_delta: dict[str, Any], adk_event: ADKEvent | None = None
    ) -> StateDeltaEvent:
        """Create a state delta event from a state change dictionary.

        Converts state changes into JSON Patch format operations for AGUI consumption.
        Each key-value pair becomes an "add" operation with the appropriate path.

        Args:
            :param state_delta: Dictionary containing state changes to apply

        Returns:
            StateDeltaEvent with JSON Patch operations
        """
        patches = []
        for key, value in state_delta.items():
            patches.append({"op": "add", "path": f"/{key}", "value": value})
        return self.state_event_util.create_state_delta_event_with_json_patch(
            patches, adk_event=self._add_adk_event(adk_event)
        )

    def create_state_snapshot_event(
        self, state_snapshot: dict[str, Any], adk_event: ADKEvent | None = None
    ) -> StateSnapshotEvent:
        """Create a state snapshot event with complete state data.

        Delegates to the state event utility to create a properly formatted
        StateSnapshotEvent containing the current session state.

        Args:
            :param state_snapshot: Dictionary containing the complete session state

        Returns:
            StateSnapshotEvent containing the full state snapshot
        """
        return self.state_event_util.create_state_snapshot_event(
            state_snapshot, adk_event=self._add_adk_event(adk_event)
        )

    async def force_close_streaming_message(self) -> AsyncGenerator[BaseEvent]:
        """Force close any active streaming message that wasn't properly terminated.

        This method is used to clean up streaming state when transitioning to
        function calls or other operations that require a clean state.

        Yields:
            TextMessageEndEvent if there was an active streaming message
        """
        if not self._streaming_message_id:
            return
        record_warning_log(
            f"🚨 Force-closing unterminated streaming message: {self._streaming_message_id}"
        )
        for message_id in self._streaming_message_id.values():
            yield TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END, message_id=message_id
            )
        self._streaming_message_id = {}
