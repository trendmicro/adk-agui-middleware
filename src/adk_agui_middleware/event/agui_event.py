from ag_ui.core import (
    ThinkingTextMessageContentEvent,
    ThinkingTextMessageEndEvent,
    ThinkingTextMessageStartEvent,
)


class CustomerThinkingTextMessageStartEvent(ThinkingTextMessageStartEvent):
    thinking_id: str


class CustomerThinkingTextMessageContentEvent(ThinkingTextMessageContentEvent):
    thinking_id: str


class CustomerThinkingTextMessageEndEvent(ThinkingTextMessageEndEvent):
    thinking_id: str
