from ..data_model.queue import EventQueue
from ..manager.queue import QueueManager


class QueueHandler:
    def __init__(self, event_queue: EventQueue) -> None:
        self.event_queue = event_queue

    def get_adk_queue(self) -> QueueManager:
        return QueueManager(self.event_queue.adk_event_queue)

    def get_agui_queue(self) -> QueueManager:
        return QueueManager(self.event_queue.agui_event_queue)
