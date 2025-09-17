import asyncio
import time
from typing import Any

from ag_ui.core import RunErrorEvent

from ..base_abc.handler import SessionLockHandler
from ..data_model.common import InputInfo, SessionLockConfig
from ..event.error_event import AGUIErrorEvent


class DefaultSessionLockHandler(SessionLockHandler):
    def __init__(self, lock_config: SessionLockConfig):
        self.lock_config = lock_config
        self.locks: dict[str, dict[str, Any]] = {}
        self.internal_lock = asyncio.Lock()

    def _cleanup_expired_lock(self, session_id: str) -> None:
        if session_id not in self.locks:
            return
        if (
            time.time() - self.locks[session_id]["timestamp"]
            >= self.lock_config.lock_timeout
        ):
            del self.locks[session_id]

    async def _try_acquire_lock(self, session_id: str) -> bool:
        async with self.internal_lock:
            self._cleanup_expired_lock(session_id)
            if session_id in self.locks:
                return False
            current_time = time.time()
            self.locks[session_id] = {
                "timestamp": current_time,
                "locked_at": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(current_time)
                ),
            }
            return True

    async def lock(self, input_info: InputInfo) -> bool:
        if await self._try_acquire_lock(input_info.session_id):
            return True
        for _ in range(self.lock_config.lock_retry_times):
            await asyncio.sleep(self.lock_config.lock_retry_interval)
            if await self._try_acquire_lock(input_info.session_id):
                return True
        return False

    async def unlock(self, input_info: InputInfo) -> None:
        async with self.internal_lock:
            self._cleanup_expired_lock(input_info.session_id)

    async def check_locked(self, input_info: InputInfo) -> bool:
        async with self.internal_lock:
            self._cleanup_expired_lock(input_info.session_id)
            return input_info.session_id in self.locks

    async def get_locked_message(self, input_info: InputInfo) -> RunErrorEvent:
        return AGUIErrorEvent.create_is_locked_error(input_info.session_id)
