# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Event translation data models for ADK to AGUI event conversion."""

from ag_ui.core import BaseEvent
from google.adk.events import Event
from pydantic import BaseModel


class TranslateEvent(BaseModel):
    """Data model for translated events in the middleware pipeline.

    Represents the result of translating an ADK event to AGUI format,
    including control flags for event processing behavior. This model
    enables custom translation handlers to control both the translated
    event content and the processing flow.

    The is_retune flag allows translation handlers to signal when
    agent processing should be interrupted or modified based on
    the translated event content.

    Attributes:
        agui_event: The translated AGUI event, or None if translation failed or was skipped
        is_retune: Whether the event should trigger retuning of the agent processing flow
    """

    agui_event: BaseEvent | None = None
    adk_event: Event | None = None
    is_retune: bool = False
    is_replace: bool = False
