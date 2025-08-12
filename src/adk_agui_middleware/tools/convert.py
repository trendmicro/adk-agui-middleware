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
from loggers.record_log import record_error_log


def convert_ag_ui_messages_to_adk(messages: list[BaseMessage]) -> list[ADKEvent]:
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
            continue
    return adk_events


def _handle_assistant_message(message: AssistantMessage) -> types.Content:
    parts = []
    if message.content:
        parts.append(types.Part(text=message.content))
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
    return (
        types.Content(role=message.role, parts=[types.Part(text=message.content)])
        if message.content
        else None
    )


def convert_agui_to_adk_event(message: BaseMessage) -> types.Content | None:
    if isinstance(message, UserMessage | SystemMessage) and message.content:
        return _handle_user_system_message(message)
    if isinstance(message, AssistantMessage):
        return _handle_assistant_message(message)
    if isinstance(message, ToolMessage):
        return _handle_tool_message(message)
    return None


def _create_tool_call(function_call: FunctionCall, event_id: str) -> ToolCall:
    return ToolCall(
        id=event_id,
        type="function",
        function=FunctionCall(
            name=function_call.name,
            arguments=json.dumps(function_call.arguments) if function_call.args else "{}",
        ),
    )


def convert_adk_event_to_ag_ui_message(event: ADKEvent) -> BaseMessage | None:
    try:
        if not event.content or not event.content.parts:
            return None
        text_parts = []
        tool_calls = []
        for part in event.content.parts:
            if part.text:
                text_parts.append(part.text)
            elif part.function_call:
                tool_calls.append(_create_tool_call(part.function_call, event.id))
        content = "\n".join(text_parts) if text_parts else None
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
    patches = []
    for key, value in state_delta.items():
        if value is None:
            patches.append({"op": "remove", "path": f"/{key}"})
        else:
            patches.append({"op": "replace", "path": f"/{key}", "value": value})
    return patches


def convert_json_patch_to_state(patches: list[dict[str, Any]]) -> dict[str, Any]:
    state_delta = {}
    for patch in patches:
        op = patch.get("op")
        path = patch.get("path", "")
        key = path.lstrip("/")
        if op == "remove":
            state_delta[key] = None
        elif op in ["add", "replace"]:
            state_delta[key] = patch.get("value")
    return state_delta
