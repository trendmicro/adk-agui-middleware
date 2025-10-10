from asyncio import Queue

from ag_ui.core import BaseEvent
from google.adk.events import Event
from pydantic import BaseModel


class EventQueue(BaseModel):
    adk_event_queue: Queue[Event | None]
    agui_event_queue: Queue[BaseEvent | None]
