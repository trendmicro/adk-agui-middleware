from typing import Annotated, Literal

from ag_ui.core.types import (
    AssistantMessage,
    BaseMessage,
    DeveloperMessage,
    SystemMessage,
    ToolMessage,
    UserMessage,
)
from pydantic import Field


class ThinkingMessage(BaseMessage):
    role: Literal["thinking"] = "thinking"
    content: str


Message = Annotated[
    ThinkingMessage
    | DeveloperMessage
    | SystemMessage
    | AssistantMessage
    | UserMessage
    | ToolMessage,
    Field(discriminator="role"),
]
