# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Data model for event queue management in the middleware pipeline."""

from asyncio import Queue

from ag_ui.core import BaseEvent
from google.adk.events import Event
from pydantic import BaseModel, ConfigDict


class EventQueue(BaseModel):
    """Container for ADK and AGUI event queues used in concurrent event processing.

    This model encapsulates the dual-queue architecture of the middleware,
    where ADK events are translated to AGUI events through separate async queues.
    The queues enable concurrent processing where one task produces ADK events
    while another consumes them and produces translated AGUI events.

    The None value in queue typing serves as a sentinel to signal queue termination,
    allowing consumers to gracefully exit their processing loops.

    Attributes:
        adk_event_queue: Queue for ADK events from the agent runner
        agui_event_queue: Queue for translated AGUI events ready for client transmission
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    adk_event_queue: Queue[Event | None]
    """Queue for ADK events from the agent runner."""

    agui_event_queue: Queue[BaseEvent | None]
    """Queue for translated AGUI events ready for client transmission."""
