# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Conversion utilities for transforming AGUI events to Server-Sent Events format.

This module provides functions to convert AGUI BaseEvent objects into SSE-compatible
formats for streaming to clients. Supports both standard SSE dictionary format and
simplified string-based fake SSE format for testing and debugging.
"""

import time
import uuid

from ag_ui.core import BaseEvent


def convert_agui_event_to_str_fake_sse(event: BaseEvent) -> str:
    """Convert AGUI BaseEvent to simplified string-based fake SSE format.

    Creates a simple SSE-like string format for testing and debugging purposes.
    This format mimics SSE structure but returns a plain string instead of
    a structured dictionary, making it useful for simple streaming scenarios
    or development testing.

    Args:
        :param event: AGUI BaseEvent to convert to fake SSE string format

    Returns:
        String formatted as SSE data line with event JSON and double newline terminator
    """
    return f"data: {event.model_dump_json(by_alias=True, exclude_none=True)}\n\n"


def convert_agui_event_to_sse(event: BaseEvent) -> dict[str, str]:
    """Convert AGUI BaseEvent to Server-Sent Events format.

    Transforms an AGUI event into the standard SSE format with data, event type,
    and unique identifier. Adds timestamp and excludes null values from serialization.
    This is the core conversion function for streaming agent events to clients
    through the SSE protocol.

    The function ensures proper SSE formatting by:
    - Adding a millisecond timestamp for event tracking
    - Serializing event data as JSON with proper field exclusions
    - Providing event type for client-side event handling
    - Generating unique IDs for event correlation

    Args:
        :param event: AGUI BaseEvent to convert to SSE format

    Returns:
        Dictionary containing SSE-formatted event with 'data', 'event', and 'id' fields
    """
    # Add current timestamp in milliseconds for event tracking
    event.timestamp = int(time.time() * 1000)
    return {
        "data": event.model_dump_json(
            by_alias=True, exclude_none=True, exclude={"type"}
        ),
        "event": event.type.value,
        "id": str(uuid.uuid4()),
    }
