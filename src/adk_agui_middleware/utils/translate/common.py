"""Common translation utilities for event handling and retune operations."""

from ...data_model.event import TranslateEvent


def create_translate_retune_event() -> TranslateEvent:
    """Create a TranslateEvent with retune flag enabled.

    Creates a TranslateEvent object that signals the event processing pipeline
    to retune the agent behavior. This is typically used to modify agent
    execution flow or trigger specific processing modes.

    Returns:
        TranslateEvent object configured for retune operation with no AGUI event
    """
    return TranslateEvent(is_retune=True)
