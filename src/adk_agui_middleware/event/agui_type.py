# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""AGUI-specific message types and union definitions.

This module extends the standard AGUI message types with custom message types
specific to the ADK-AGUI middleware, such as thinking messages for displaying
AI reasoning processes.
"""

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
    """Message type for displaying AI thinking/reasoning processes.

    Represents internal AI reasoning that can be displayed to users
    for transparency and debugging purposes. This message type is
    specific to the ADK-AGUI middleware.

    Attributes:
        role: Always "thinking" to identify this message type
        content: The thinking content or reasoning text to display
    """

    role: Literal["thinking"] = "thinking"
    content: str  # The thinking content or reasoning text to display


Message = Annotated[
    ThinkingMessage
    | DeveloperMessage
    | SystemMessage
    | AssistantMessage
    | UserMessage
    | ToolMessage,
    Field(discriminator="role"),
]
"""Union type representing all possible message types in AGUI conversations.

This discriminated union includes both standard AGUI message types and
custom middleware-specific types like ThinkingMessage. The discriminator
field "role" is used to determine the specific message type during
deserialization.

Supported message types:
    - ThinkingMessage: AI reasoning/thinking processes
    - DeveloperMessage: Developer-specific messages
    - SystemMessage: System-generated messages
    - AssistantMessage: AI assistant responses
    - UserMessage: User input messages
    - ToolMessage: Tool execution results
"""
