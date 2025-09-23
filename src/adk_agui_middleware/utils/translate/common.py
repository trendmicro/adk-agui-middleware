# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Common translation utilities for event handling and retune operations."""

from google.adk.events import Event

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


def create_translate_replace_adk_event(event: Event) -> TranslateEvent:
    """Create a TranslateEvent that replaces the current ADK event.

    Creates a TranslateEvent object configured to replace the current ADK event
    in the translation pipeline. This allows custom translation handlers to
    substitute events during processing, enabling event transformation or
    modification before standard translation.

    Args:
        :param event: ADK event to use as replacement in the translation pipeline

    Returns:
        TranslateEvent object configured for ADK event replacement
    """
    return TranslateEvent(adk_event=event, is_replace=True)
