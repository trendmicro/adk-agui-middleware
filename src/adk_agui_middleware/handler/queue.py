# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Handler for managing event queue access and manager creation."""

from ..data_model.queue import EventQueue
from ..manager.queue import QueueManager


class QueueHandler:
    """Provides managed access to ADK and AGUI event queues.

    Acts as a factory for QueueManager instances, wrapping the raw asyncio queues
    with management functionality like logging and iteration support. This handler
    simplifies queue access for components that need to interact with the event
    pipeline.

    Attributes:
        event_queue: Container holding both ADK and AGUI event queues
    """

    def __init__(self, event_queue: EventQueue) -> None:
        """Initialize the queue handler with event queues.

        Args:
            :param event_queue: EventQueue model containing ADK and AGUI queues
        """
        self.event_queue = event_queue

    def get_adk_queue(self) -> QueueManager:
        """Get a managed ADK event queue.

        Returns:
            QueueManager wrapping the ADK event queue with logging and iteration support
        """
        return QueueManager(self.event_queue.adk_event_queue)

    def get_agui_queue(self) -> QueueManager:
        """Get a managed AGUI event queue.

        Returns:
            QueueManager wrapping the AGUI event queue with logging and iteration support
        """
        return QueueManager(self.event_queue.agui_event_queue)
