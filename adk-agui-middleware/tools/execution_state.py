import asyncio
import time

from loggers.record_log import record_debug_log


class ExecutionState:
    def __init__(self, task: asyncio.Task, thread_id: str, event_queue: asyncio.Queue):
        self.task = task
        self.thread_id = thread_id
        self.event_queue = event_queue
        self.start_time = time.time()
        self.is_complete = False
        self.pending_tool_calls: set[str] = set()

        record_debug_log(f"Created execution state for thread {thread_id}")

    def is_stale(self, timeout_seconds: int) -> bool:
        return time.time() - self.start_time > timeout_seconds

    async def cancel(self):
        record_debug_log(f"Cancelling execution for thread {self.thread_id}")
        if not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.is_complete = True

    def get_execution_time(self) -> float:
        return time.time() - self.start_time

    def add_pending_tool_call(self, tool_call_id: str):
        self.pending_tool_calls.add(tool_call_id)
        record_debug_log(
            f"Added pending tool call {tool_call_id} to thread {self.thread_id}"
        )

    def remove_pending_tool_call(self, tool_call_id: str):
        self.pending_tool_calls.discard(tool_call_id)
        record_debug_log(
            f"Removed pending tool call {tool_call_id} from thread {self.thread_id}"
        )

    def has_pending_tool_calls(self) -> bool:
        return len(self.pending_tool_calls) > 0

    def get_status(self) -> str:
        if self.is_complete:
            if self.has_pending_tool_calls():
                return "complete_awaiting_tools"
            return "complete"
        if self.task.done():
            return "task_done"
        return "running"

    def __repr__(self) -> str:
        return (
            f"ExecutionState(thread_id='{self.thread_id}', "
            f"status='{self.get_status()}', "
            f"runtime={self.get_execution_time():.1f}s)"
        )
