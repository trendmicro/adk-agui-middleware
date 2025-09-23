# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Default implementation of session locking for preventing concurrent access."""

import asyncio
import time
from typing import Any

from ag_ui.core import RunErrorEvent

from ..base_abc.handler import SessionLockHandler
from ..data_model.common import InputInfo, SessionLockConfig
from ..event.error_event import AGUIErrorEvent


class DefaultSessionLockHandler(SessionLockHandler):
    """Default session lock handler implementation using in-memory locks with timeout.

    Provides thread-safe session locking with automatic timeout and cleanup to prevent
    concurrent access to session data. Uses asyncio locks internally for concurrency
    control and implements retry logic for lock acquisition.

    Key Features:
    - Automatic timeout-based lock cleanup to prevent deadlocks
    - Configurable retry mechanism for lock acquisition
    - Thread-safe lock management using asyncio.Lock
    - In-memory lock storage with timestamp tracking
    - Graceful error handling for locked sessions
    """

    def __init__(self, lock_config: SessionLockConfig):
        """Initialize the session lock handler with configuration.

        Sets up the lock handler with the provided configuration and initializes
        internal data structures for tracking session locks and timestamps.

        Args:
            :param lock_config: Configuration object containing lock timeout and retry settings
        """
        self.lock_config = lock_config
        # Dictionary to store session locks with metadata
        # Structure: {session_id: {"timestamp": float, "locked_at": str}}
        self.locks: dict[str, dict[str, Any]] = {}
        # Internal asyncio lock to ensure thread-safe access to locks dictionary
        self.internal_lock = asyncio.Lock()

    def _cleanup_expired_lock(self, session_id: str) -> None:
        """Clean up expired locks based on configured timeout.

        Removes locks that have exceeded the configured timeout duration to prevent
        permanent lock situations. This method is called automatically during lock
        operations to maintain lock hygiene.

        Args:
            :param session_id: Session identifier to check for expiration

        Note:
            This method should only be called while holding the internal lock
            to ensure thread safety during lock dictionary modifications.
        """
        if session_id not in self.locks:
            return
        # Check if lock has exceeded the configured timeout
        if (
            time.time() - self.locks[session_id]["timestamp"]
            >= self.lock_config.lock_timeout
        ):
            del self.locks[session_id]

    async def _try_acquire_lock(self, session_id: str) -> bool:
        """Attempt to acquire a lock for the specified session.

        Tries to acquire an exclusive lock for the session, cleaning up expired
        locks first and then checking availability. If successful, records the
        lock with timestamp and formatted acquisition time.

        Args:
            :param session_id: Session identifier to lock

        Returns:
            True if lock was successfully acquired, False if session is already locked

        Note:
            This method is thread-safe and handles internal lock management.
        """
        async with self.internal_lock:
            # Clean up any expired locks first
            self._cleanup_expired_lock(session_id)

            # Check if session is already locked
            if session_id in self.locks:
                return False

            # Acquire lock by recording current time and readable timestamp
            current_time = time.time()
            self.locks[session_id] = {
                "timestamp": current_time,
                "locked_at": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(current_time)
                ),
            }
            return True

    async def lock(self, input_info: InputInfo) -> bool:
        """Acquire a lock for the session with retry logic.

        Attempts to acquire a session lock, implementing retry logic with
        configurable delays and maximum retry attempts. This is the main
        entry point for acquiring session locks.

        Args:
            :param input_info: Input information containing session identifiers

        Returns:
            True if lock was successfully acquired, False if all retry attempts failed
        """
        # Try immediate acquisition first
        if await self._try_acquire_lock(input_info.session_id):
            return True

        # Implement retry logic with configurable delays
        for _ in range(self.lock_config.lock_retry_times):
            await asyncio.sleep(self.lock_config.lock_retry_interval)
            if await self._try_acquire_lock(input_info.session_id):
                return True

        # All retry attempts failed
        return False

    async def unlock(self, input_info: InputInfo) -> None:
        """Release the lock for the specified session.

        Removes the session lock, allowing other requests to access the session.
        Also performs cleanup of expired locks during the operation.

        Args:
            :param input_info: Input information containing session identifiers
        """
        async with self.internal_lock:
            if input_info.session_id in self.locks:
                del self.locks[input_info.session_id]

    async def get_locked_message(self, input_info: InputInfo) -> RunErrorEvent:
        """Generate an error event indicating that the session is locked.

        Creates a standardized error event to inform clients that the requested
        session is currently locked and unavailable for processing.

        Args:
            :param input_info: Input information containing session identifiers

        Returns:
            RunErrorEvent with session locked error details
        """
        return AGUIErrorEvent.create_is_locked_error(input_info.session_id)
