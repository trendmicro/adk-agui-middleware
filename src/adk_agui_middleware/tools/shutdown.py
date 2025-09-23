# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Graceful shutdown handler for managing application cleanup and signal handling."""

import asyncio
import signal
from collections.abc import Awaitable, Callable
from typing import Any

from ..loggers.record_log import record_error_log, record_log
from ..pattern.singleton import Singleton


class ShutdownHandler(metaclass=Singleton):
    """Singleton handler for graceful application shutdown and cleanup operations.

    Manages signal handling (SIGTERM, SIGINT, SIGHUP) and coordinates the
    execution of registered shutdown functions when termination signals are received.
    Ensures proper cleanup of resources before application termination.
    """

    def __init__(self) -> None:
        """Initialize the shutdown handler and set up signal handlers."""
        self._shutdown_list: list[Callable[[], Awaitable[None]]] = []
        self._shutdown_in_progress = False
        self._setup_signal_handlers()

    def register_shutdown_function(
        self,
        shutdown_function: Callable[[], Awaitable[None]],
    ) -> None:
        """Register a function to be called during graceful shutdown.

        Adds an async function to the shutdown sequence that will be called
        when the application receives termination signals. Useful for cleanup
        operations like closing database connections, stopping runners, etc.

        Args:
            :param shutdown_function: Async function to call during shutdown process
        """
        self._shutdown_list.append(shutdown_function)

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown on common termination signals.

        Registers signal handlers for SIGTERM, SIGINT, and SIGHUP to ensure
        graceful shutdown when the application receives these signals.
        """
        for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP]:
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:  # noqa: ARG002
        """Handle termination signals by initiating graceful shutdown.

        Called when the application receives termination signals. Initiates
        the graceful shutdown process to ensure all resources are properly
        cleaned up before the application exits.

        Args:
            :param signum: Signal number that was received
            :param frame: Current stack frame (unused)
        """
        if self._shutdown_in_progress:
            return

        record_log(f"Received signal {signum}, initiating graceful shutdown")
        self._shutdown_in_progress = True

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self._graceful_shutdown())
                return
        except RuntimeError:
            pass
        asyncio.run(self._graceful_shutdown())

    async def _graceful_shutdown(self) -> None:
        """Execute all registered shutdown functions in sequence.

        Calls all registered shutdown functions and handles any errors that occur.
        Ensures the event loop is properly stopped after shutdown completion.
        """
        try:
            await self.close()
            record_log("Shutdown functions completed successfully")
        except Exception as e:
            record_error_log("Error during graceful shutdown", e)
        finally:
            try:
                loop = asyncio.get_running_loop()
                loop.call_later(1, loop.stop)
            except RuntimeError:
                pass

    async def close(self) -> None:
        """Close all registered shutdown functions with individual error handling.

        Iterates through all registered shutdown functions and calls them,
        logging any errors that occur without stopping the shutdown process.
        This ensures that all cleanup operations are attempted even if some fail.
        """
        for shutdown_function in self._shutdown_list:
            try:
                await shutdown_function()
            except Exception as e:
                record_error_log(
                    f"Error in shutdown function {shutdown_function.__name__}", e
                )
