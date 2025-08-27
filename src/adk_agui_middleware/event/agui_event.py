"""Custom AGUI thinking event implementations with enhanced tracking capabilities."""

from ag_ui.core import (
    ThinkingTextMessageContentEvent,
    ThinkingTextMessageEndEvent,
    ThinkingTextMessageStartEvent,
)


class CustomerThinkingTextMessageStartEvent(ThinkingTextMessageStartEvent):
    """Extended thinking text message start event with custom thinking ID tracking.
    
    Extends the base ThinkingTextMessageStartEvent to include a custom thinking_id
    field for enhanced tracking and correlation of thinking message sequences.
    """
    
    thinking_id: str
    """Unique identifier for correlating thinking message sequences."""


class CustomerThinkingTextMessageContentEvent(ThinkingTextMessageContentEvent):
    """Extended thinking text message content event with custom thinking ID tracking.
    
    Extends the base ThinkingTextMessageContentEvent to include a custom thinking_id
    field for enhanced tracking and correlation of thinking message content.
    """
    
    thinking_id: str
    """Unique identifier for correlating thinking message sequences."""


class CustomerThinkingTextMessageEndEvent(ThinkingTextMessageEndEvent):
    """Extended thinking text message end event with custom thinking ID tracking.
    
    Extends the base ThinkingTextMessageEndEvent to include a custom thinking_id
    field for enhanced tracking and correlation of thinking message sequences.
    """
    
    thinking_id: str
    """Unique identifier for correlating thinking message sequences."""
