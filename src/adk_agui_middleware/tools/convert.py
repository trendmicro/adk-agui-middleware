"""Event conversion utilities for Server-Sent Events format."""

import time
import uuid

from ag_ui.core import BaseEvent


def agui_to_sse(event: BaseEvent) -> dict[str, str]:
    """Convert AGUI BaseEvent to Server-Sent Events format.
    
    Transforms an AGUI event into the standard SSE format with data, event type,
    and unique identifier. Adds timestamp and excludes null values from serialization.
    
    Args:
        event: AGUI BaseEvent to convert to SSE format
        
    Returns:
        Dictionary containing SSE-formatted event with data, event, and id fields
    """
    event.timestamp = int(time.time() * 1000)
    return {
        "data": event.model_dump_json(
            by_alias=True, exclude_none=True, exclude={"type"}
        ),
        "event": event.type.value,
        "id": str(uuid.uuid4()),
    }
