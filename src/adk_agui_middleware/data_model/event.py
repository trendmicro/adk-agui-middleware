"""Event translation data models for ADK to AGUI event conversion."""

from ag_ui.core import BaseEvent


class TranslateEvent:
    """Data model for translated events in the middleware pipeline.

    Represents the result of translating an ADK event to AGUI format,
    including control flags for event processing behavior.

    Attributes:
        agui_event: The translated AGUI event, or None if translation failed
        is_retune: Whether the event should trigger retuning of the agent
        is_skip: Whether this event should be skipped in processing
    """

    agui_event: BaseEvent | None = None
    is_retune: bool = True
    is_skip: bool = False
