from typing import Any, cast

from ag_ui.core import (
    BaseEvent,
    TextMessageContentEvent,
    ToolCallArgsEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.core.types import (
    AssistantMessage,
    FunctionCall,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)

from ..event.agui_event import CustomThinkingTextMessageContentEvent
from ..event.agui_type import Message, ThinkingMessage


class ConvertADKEventToAGUIMessage:
    def __init__(self) -> None:
        self.accumulator: dict[str, dict[str, Any]] = {}

    def _append_content(self, key: str, msg_type: str, delta: str) -> None:
        if key not in self.accumulator:
            self.accumulator[key] = {"type": msg_type, "content": ""}
        self.accumulator[key]["content"] += delta

    def _init_tool(self, key: str) -> None:
        if key not in self.accumulator:
            self.accumulator[key] = {"type": "tool", "name": "", "arg": ""}

    def _classify_and_merge(self, messages: list[BaseEvent | UserMessage]) -> None:
        for event in messages:
            if isinstance(event, CustomThinkingTextMessageContentEvent):
                self._append_content(event.thinking_id, "thinking", event.delta)
            elif isinstance(event, TextMessageContentEvent):
                self._append_content(event.message_id, "message", event.delta)
            elif isinstance(event, ToolCallArgsEvent):
                self._init_tool(event.tool_call_id)
                self.accumulator[event.tool_call_id]["arg"] += event.delta
            elif isinstance(event, ToolCallStartEvent):
                self._init_tool(event.tool_call_id)
                self.accumulator[event.tool_call_id]["name"] = event.tool_call_name
            elif isinstance(event, UserMessage):
                self.accumulator[event.id] = {"type": "user", "content": event}
            elif isinstance(event, ToolCallResultEvent):
                self.accumulator[f"{event.tool_call_id}_result"] = {
                    "type": "tool_result",
                    "content": event.content,
                    "tool_call_id": event.tool_call_id,
                    "message_id": event.message_id,
                }

    @staticmethod
    def _create_message(key: str, data: dict[str, Any]) -> Message | None:
        msg_type = data["type"]
        if msg_type == "thinking":
            return ThinkingMessage(id=key, content=data["content"])
        if msg_type == "message":
            return SystemMessage(id=key, content=data["content"])
        if msg_type == "user":
            return cast(UserMessage, data.get("content"))
        if msg_type == "tool":
            return AssistantMessage(
                id=key,
                tool_calls=[
                    ToolCall(
                        id=key,
                        function=FunctionCall(name=data["name"], arguments=data["arg"]),
                    )
                ],
            )
        if msg_type == "tool_result":
            return ToolMessage(
                id=data["message_id"],
                tool_call_id=data["tool_call_id"],
                content=data["content"],
            )
        return None

    def convert(self, messages: list[BaseEvent | UserMessage]) -> list[Message]:
        self._classify_and_merge(messages)
        result: list[Message] = []
        for key, data in self.accumulator.items():
            if message := self._create_message(key, data):
                result.append(message)
        return result
