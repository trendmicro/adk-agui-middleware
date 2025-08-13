"""Message conversion utilities between AGUI and ADK formats."""

import json
from typing import Any

from ag_ui.core import (
    AssistantMessage,
    BaseMessage,
    FunctionCall,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from google.adk.events import Event as ADKEvent
from google.genai import types

from ..loggers.record_log import record_error_log


def convert_ag_ui_messages_to_adk(messages: list[BaseMessage]) -> list[ADKEvent]:
    """Convert a list of AGUI messages to ADK events.

    Transforms AGUI BaseMessage objects into ADK Event objects for processing
    by the Agent Development Kit. Handles conversion errors gracefully.

    Args:
        messages: List of AGUI BaseMessage objects to convert

    Returns:
        List of ADK Event objects, excluding messages that failed conversion
    """
    adk_events = []
    for message in messages:
        try:
            adk_events.append(
                ADKEvent(
                    id=message.id,
                    author=message.role,
                    content=convert_agui_to_adk_event(message),
                )
            )
        except Exception as e:
            record_error_log(f"Error converting message {message.id}.", e)
    return adk_events


def _handle_assistant_message(message: AssistantMessage) -> types.Content:
    """Convert an AssistantMessage to Google GenAI Content format.

    Handles both text content and tool calls, creating appropriate parts
    for each component of the assistant's response.

    Args:
        message: AGUI AssistantMessage to convert

    Returns:
        Google GenAI Content object with model role, or None if no content
    """
    parts = []
    # Add text content if present
    if message.content:
        parts.append(types.Part(text=message.content))

    # Add tool calls as function call parts
    if message.tool_calls:
        tool_parts = [
            types.Part(
                function_call=types.FunctionCall(
                    name=tool_call.function.name,
                    args=json.loads(tool_call.function.arguments),
                    id=tool_call.id,
                )
            )
            for tool_call in message.tool_calls
        ]
        parts.extend(tool_parts)

    return types.Content(role="model", parts=parts) if parts else None


def _handle_tool_message(message: ToolMessage) -> types.Content:
    """Convert a ToolMessage to Google GenAI Content format.

    Transforms tool result messages into function response format
    suitable for ADK processing.

    Args:
        message: AGUI ToolMessage containing tool execution results

    Returns:
        Google GenAI Content object with function role and response
    """
    return types.Content(
        role="function",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    name=message.tool_call_id,
                    response={"result": message.content},
                    id=message.tool_call_id,
                )
            )
        ],
    )


def _handle_user_system_message(
    message: UserMessage | SystemMessage,
) -> types.Content | None:
    """Convert UserMessage or SystemMessage to Google GenAI Content format.

    Handles basic text messages from users or system instructions.

    Args:
        message: AGUI UserMessage or SystemMessage to convert

    Returns:
        Google GenAI Content object with text content, or None if no content
    """
    return (
        types.Content(role=message.role, parts=[types.Part(text=message.content)])
        if message.content
        else None
    )


def convert_agui_to_adk_event(message: BaseMessage) -> types.Content | None:
    """Convert any AGUI message to ADK-compatible content format.

    Routes different message types to their specific conversion handlers.

    Args:
        message: AGUI BaseMessage to convert

    Returns:
        Google GenAI Content object, or None if message type not supported
    """
    if isinstance(message, UserMessage | SystemMessage) and message.content:
        return _handle_user_system_message(message)
    if isinstance(message, AssistantMessage):
        return _handle_assistant_message(message)
    if isinstance(message, ToolMessage):
        return _handle_tool_message(message)
    return None


def _create_tool_call(function_call: FunctionCall, event_id: str) -> ToolCall:
    """Create an AGUI ToolCall from a function call and event ID.

    Args:
        function_call: Function call information from ADK
        event_id: Event identifier to use for the tool call

    Returns:
        AGUI ToolCall object with function details
    """
    return ToolCall(
        id=event_id,
        type="function",
        function=FunctionCall(
            name=function_call.name,
            arguments=json.dumps(function_call.arguments)
            if function_call.args
            else "{}",
        ),
    )


def convert_adk_event_to_ag_ui_message(event: ADKEvent) -> BaseMessage | None:
    """Convert an ADK event back to an AGUI message format.

    Extracts text content and function calls from ADK events and creates
    appropriate AGUI message objects.

    Args:
        event: ADK Event to convert

    Returns:
        AGUI BaseMessage (UserMessage or AssistantMessage), or None on error
    """
    try:
        if not event.content or not event.content.parts:
            return None

        text_parts = []
        tool_calls = []

        # Extract text and function calls from event parts
        for part in event.content.parts:
            if part.text:
                text_parts.append(part.text)
            elif part.function_call:
                tool_calls.append(_create_tool_call(part.function_call, event.id))

        # Combine text parts into single content string
        content = "\n".join(text_parts) if text_parts else None

        # Create appropriate message based on author
        if event.author == "user":
            return (
                UserMessage(id=event.id, role="user", content=content)
                if content
                else None
            )

        return AssistantMessage(
            id=event.id,
            role="assistant",
            content=content,
            tool_calls=tool_calls if tool_calls else None,
        )
    except Exception as e:
        record_error_log(f"Error converting ADK event {event.id}.", e)
        return None


def convert_state_to_json_patch(state_delta: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert state changes to JSON Patch format.

    Transforms state delta dictionary into JSON Patch operations
    for standardized state updates.

    Args:
        state_delta: Dictionary of state changes (key-value pairs)

    Returns:
        List of JSON Patch operations (remove for None values, replace for others)
    """
    patches = []
    for key, value in state_delta.items():
        if value is None:
            # None values become remove operations
            patches.append({"op": "remove", "path": f"/{key}"})
        else:
            # All other values become replace operations
            patches.append({"op": "replace", "path": f"/{key}", "value": value})
    return patches


def convert_json_patch_to_state(patches: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert JSON Patch operations back to state delta format.

    Transforms JSON Patch operations into a simple state dictionary
    for easier manipulation and processing.

    Args:
        patches: List of JSON Patch operation dictionaries

    Returns:
        Dictionary representing state changes (None for removals)
    """
    state_delta = {}
    for patch in patches:
        op = patch.get("op")
        path = patch.get("path", "")
        key = path.lstrip("/")  # Remove leading slash from path

        if op == "remove":
            # Remove operations become None values
            state_delta[key] = None
        elif op in ["add", "replace"]:
            # Add/replace operations use the patch value
            state_delta[key] = patch.get("value")

    return state_delta
