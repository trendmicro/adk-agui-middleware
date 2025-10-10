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
        adk_event: Replacement ADK event to inject into the pipeline (when is_replace is True)
        is_retune: Whether the event should trigger retuning of the agent processing flow
        is_replace: Whether to replace the current ADK event with the provided adk_event
    """

    agui_event: BaseEvent | None = None
    adk_event: Event | None = None
    is_retune: bool = False
    is_replace: bool = False
