from ...data_model.event import TranslateEvent


def translate_retune_event() -> TranslateEvent:
    """Create a TranslateEvent with retune flag enabled.

    Returns:
        TranslateEvent: Event object configured for retune operation.
    """
    return TranslateEvent(is_retune=True)
