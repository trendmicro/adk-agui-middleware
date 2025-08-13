import json
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
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from google.adk.events import Event as ADKEvent
from google.genai import types

from ..loggers.record_log import (
    record_debug_log,
    record_error_log,
    record_warning_log,
)


class EventTranslator:
    """Translates events between ADK (Agent Development Kit) and AGUI formats.

    Handles the complex conversion of ADK events to AGUI events, managing streaming
    messages, tool calls, function calls, and state updates. Maintains internal state
    for streaming operations and long-running tool executions.
    """

    def __init__(self):
        """Initialize the event translator with empty state containers."""
        self._active_tool_calls: dict[str, str] = {}  # Track active tool call IDs
        self._streaming_message_id: str | None = None  # Current streaming message ID
        self._is_streaming: bool = False  # Whether currently streaming a message
        self.long_running_tool_ids: list[str] = []  # IDs of long-running tools

    async def translate(self, adk_event: ADKEvent) -> AsyncGenerator[BaseEvent]:
        """Translate an ADK event into corresponding AGUI events.

        Processes different types of ADK events (text content, function calls,
        function responses, state updates) and yields appropriate AGUI events.

        Args:
            adk_event: ADK event to translate

        Yields:
            BaseEvent objects in AGUI format
        """
        try:
            # Skip user-authored events as they don't need translation
            if adk_event.author == "user":
                return
            # Handle text content streaming
            if adk_event.content and adk_event.content.parts:
                async for event in self._translate_text_content(adk_event):
                    yield event
            # Handle function calls with proper streaming closure
            if adk_event.get_function_calls():
                async for event in self._handle_function_calls(adk_event):
                    yield event
            # Handle function responses from tool execution
            if adk_event.get_function_responses():
                async for event in self.translate_function_response(
                    adk_event.get_function_responses()
                ):
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

        Args:
            adk_event: ADK event containing function calls

        Yields:
            BaseEvent objects for function call handling
        """
        # Force close any active streaming message before handling function calls
        async for event in self.force_close_streaming_message():
            yield event
        # Translate the function calls to AGUI events
        async for event in self.translate_function_calls(
            adk_event.get_function_calls()
        ):
            yield event

    async def _handle_additional_data(
        self, adk_event: ADKEvent
    ) -> AsyncGenerator[BaseEvent]:
        """Handle additional data like state deltas and custom metadata.

        Args:
            adk_event: ADK event potentially containing additional data

        Yields:
            BaseEvent objects for state updates and custom events
        """
        # Handle state delta updates
        if adk_event.actions and adk_event.actions.state_delta:
            yield self.create_state_delta_event(adk_event.actions.state_delta)
        # Handle custom metadata as custom events
        if adk_event.custom_metadata:
            yield CustomEvent(
                type=EventType.CUSTOM,
                name="adk_custom_metadata",
                value=adk_event.custom_metadata,
            )

    async def _translate_text_content(
        self, adk_event: ADKEvent
    ) -> AsyncGenerator[BaseEvent]:
        text_parts = [part.text for part in adk_event.content.parts if part.text]
        if not text_parts:
            return
        if adk_event.is_final_response():
            if not (self._is_streaming and self._streaming_message_id):
                return
            yield TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END, message_id=self._streaming_message_id
            )
            self._streaming_message_id = None
            self._is_streaming = False
            return

        if not self._is_streaming:
            self._streaming_message_id = str(uuid.uuid4())
            self._is_streaming = True
            yield TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=self._streaming_message_id,
                role="assistant",
            )

        if combined_text := "".join(text_parts):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=self._streaming_message_id,
                delta=combined_text,
            )

        if adk_event.is_final_response() and not adk_event.partial:
            yield TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END, message_id=self._streaming_message_id
            )
            self._streaming_message_id = None
            self._is_streaming = False

    async def translate_lro_function_calls(
        self, adk_event: ADKEvent
    ) -> AsyncGenerator[BaseEvent]:
        if not (adk_event.content and adk_event.content.parts):
            return
        for part in adk_event.content.parts:
            if (
                (not part.function_call)
                or part.function_call.id not in adk_event.long_running_tool_ids
                or []
            ):
                continue
            self.long_running_tool_ids.append(part.function_call.id)
            yield ToolCallStartEvent(
                type=EventType.TOOL_CALL_START,
                tool_call_id=part.function_call.id,
                tool_call_name=part.function_call.name,
                parent_message_id=None,
            )
            if part.function_call.args:
                yield ToolCallArgsEvent(
                    type=EventType.TOOL_CALL_ARGS,
                    tool_call_id=part.function_call.id,
                    delta=(
                        json.dumps(part.function_call.args)
                        if isinstance(part.function_call.args, dict)
                        else str(part.function_call.args)
                    ),
                )
            yield ToolCallEndEvent(
                type=EventType.TOOL_CALL_END, tool_call_id=part.function_call.id
            )
            self._active_tool_calls.pop(part.function_call.id, None)

    async def translate_function_calls(
        self,
        function_calls: list[types.FunctionCall],
    ) -> AsyncGenerator[BaseEvent]:
        parent_message_id = None
        for func_call in function_calls:
            tool_call_id = func_call.id or str(uuid.uuid4())
            self._active_tool_calls[tool_call_id] = tool_call_id
            yield ToolCallStartEvent(
                type=EventType.TOOL_CALL_START,
                tool_call_id=tool_call_id,
                tool_call_name=func_call.name,
                parent_message_id=parent_message_id,
            )
            if func_call.args:
                args_str = (
                    json.dumps(func_call.args)
                    if isinstance(func_call.args, dict)
                    else str(func_call.args)
                )
                yield ToolCallArgsEvent(
                    type=EventType.TOOL_CALL_ARGS,
                    tool_call_id=tool_call_id,
                    delta=args_str,
                )
            yield ToolCallEndEvent(
                type=EventType.TOOL_CALL_END, tool_call_id=tool_call_id
            )
            self._active_tool_calls.pop(tool_call_id, None)

    async def translate_function_response(
        self,
        function_response: list[types.FunctionResponse],
    ) -> AsyncGenerator[BaseEvent]:
        for func_response in function_response:
            tool_call_id = func_response.id or str(uuid.uuid4())
            if tool_call_id not in self.long_running_tool_ids:
                yield ToolCallResultEvent(
                    message_id=str(uuid.uuid4()),
                    type=EventType.TOOL_CALL_RESULT,
                    tool_call_id=tool_call_id,
                    content=json.dumps(func_response.response),
                )
            else:
                record_debug_log(
                    f"Skipping ToolCallResultEvent for long-running tool: {tool_call_id}"
                )

    @staticmethod
    def create_state_delta_event(state_delta: dict[str, Any]) -> StateDeltaEvent:
        patches = []
        for key, value in state_delta.items():
            patches.append({"op": "add", "path": f"/{key}", "value": value})
        return StateDeltaEvent(type=EventType.STATE_DELTA, delta=patches)

    @staticmethod
    def create_state_snapshot_event(
        state_snapshot: dict[str, Any],
    ) -> StateSnapshotEvent:
        return StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT, snapshot=state_snapshot
        )

    async def force_close_streaming_message(self) -> AsyncGenerator[BaseEvent]:
        """Force close any active streaming message that wasn't properly terminated.

        This method is used to clean up streaming state when transitioning to
        function calls or other operations that require a clean state.

        Yields:
            TextMessageEndEvent if there was an active streaming message
        """
        if not (self._is_streaming and self._streaming_message_id):
            return
        record_warning_log(
            f"🚨 Force-closing unterminated streaming message: {self._streaming_message_id}"
        )
        end_event = TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END, message_id=self._streaming_message_id
        )
        yield end_event
        self._streaming_message_id = None
        self._is_streaming = False
