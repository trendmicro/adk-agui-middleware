"""Event translation data models for ADK to AGUI event conversion."""

from ag_ui.core import BaseEvent
from pydantic import BaseModel


class TranslateEvent(BaseModel):
    """Data model for translated events in the middleware pipeline.

    Represents the result of translating an ADK event to AGUI format,
    including control flags for event processing behavior.

    Attributes:
        agui_event: The translated AGUI event, or None if translation failed
        is_retune: Whether the event should trigger retuning of the agent
    """

    agui_event: BaseEvent | None = None
    is_retune: bool = False
