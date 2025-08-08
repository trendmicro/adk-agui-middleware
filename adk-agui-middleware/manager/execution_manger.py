import asyncio

from loggers.record_log import record_log, record_error_log
from manager.session_manager import SessionHandler
from tools.execution_state import ExecutionState


class ExecutionManger:
    def __init__(self):
        self._active_executions: dict[str, ExecutionState] = {}
        self._execution_lock = asyncio.Lock()
        self._execution_timeout = 10
        self._max_concurrent = 5

    async def _cleanup_stale_executions(self):
        stale_sessions = []
        for session_id, execution in self._active_executions.items():
            if execution.is_stale(self._execution_timeout):
                stale_sessions.append(session_id)
        for session_id in stale_sessions:
            execution = self._active_executions.pop(session_id)
            await execution.cancel()
            record_log(f"Cleaned up stale execution for session {session_id}")

    async def check_existing_execution(self, session_id: str):
        async with self._execution_lock:
            if len(self._active_executions) >= self._max_concurrent:
                await self._cleanup_stale_executions()
                if len(self._active_executions) >= self._max_concurrent:
                    raise RuntimeError(
                        f"Maximum concurrent executions ({self._max_concurrent}) reached"
                    )
            existing_execution = self._active_executions.get(session_id)
        if existing_execution and not existing_execution.is_complete:
            try:
                await existing_execution.task
            except Exception as e:
                record_error_log("Previous execution completed with error.", e)

    async def lock_execution(self, session_id: str, execution: ExecutionState):
        async with self._execution_lock:
            self._active_executions[session_id] = execution

    async def unlock_execution(self, session_id: str, session_handler: SessionHandler):
        async with self._execution_lock:
            if session_id not in self._active_executions:
                return
            execution = self._active_executions[session_id]
            execution.is_complete = True
            if not await session_handler.get_pending_tool_calls():
                del self._active_executions[session_id]
                record_log(f"Cleaned up execution for session {session_id}")
                return
            record_log(f"Preserving execution for session {session_id} - has pending tool calls (HITL scenario)")
