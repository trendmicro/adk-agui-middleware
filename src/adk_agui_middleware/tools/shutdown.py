import asyncio
import signal
from collections.abc import Awaitable, Callable
from typing import Any

from loggers.record_log import record_error_log, record_log
from pattern.singleton import Singleton


class ShutdownHandler(metaclass=Singleton):
    def __init__(self):
        self._shutdown_list = []
        self._shutdown_in_progress = False
        self._setup_signal_handlers()

    def register_shutdown_function(
        self, shutdown_function: Callable[[], Awaitable]
    ) -> None:
        self._shutdown_list.append(shutdown_function)

    def _setup_signal_handlers(self) -> None:
        for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP]:
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:  # noqa: ARG002
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
        for shutdown_function in self._shutdown_list:
            try:
                await shutdown_function()
            except Exception as e:
                record_error_log(
                    f"Error in shutdown function {shutdown_function.__name__}", e
                )
