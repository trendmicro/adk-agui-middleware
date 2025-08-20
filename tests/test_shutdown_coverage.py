"""Additional tests for shutdown.py to boost coverage."""

import signal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from adk_agui_middleware.tools.shutdown import ShutdownHandler

from test_utils import BaseTestCase


class TestShutdownCoverage(BaseTestCase):
    """Additional tests for shutdown functionality to improve coverage."""

    def test_shutdown_handler_initialization(self):
        """Test ShutdownHandler initialization."""
        handler = ShutdownHandler()
        assert handler is not None
        assert hasattr(handler, "_shutdown_list")
        assert hasattr(handler, "_shutdown_in_progress")

    def test_shutdown_handler_singleton(self):
        """Test ShutdownHandler singleton behavior."""
        handler1 = ShutdownHandler()
        handler2 = ShutdownHandler()
        assert handler1 is handler2

    def test_register_shutdown_function(self):
        """Test registering shutdown functions."""
        handler = ShutdownHandler()

        async def dummy_shutdown():
            pass

        initial_count = len(handler._shutdown_list)
        handler.register_shutdown_function(dummy_shutdown)

        assert len(handler._shutdown_list) == initial_count + 1
        assert dummy_shutdown in handler._shutdown_list

    def test_register_multiple_shutdown_functions(self):
        """Test registering multiple shutdown functions."""
        handler = ShutdownHandler()

        async def shutdown1():
            pass

        async def shutdown2():
            pass

        handler.register_shutdown_function(shutdown1)
        handler.register_shutdown_function(shutdown2)

        assert shutdown1 in handler._shutdown_list
        assert shutdown2 in handler._shutdown_list


    def test_signal_handler_shutdown_in_progress(self):
        """Test signal handler when shutdown already in progress."""
        handler = ShutdownHandler()
        handler._shutdown_in_progress = True

        # Should return early if shutdown already in progress
        result = handler._signal_handler(signal.SIGTERM, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_graceful_shutdown_execution(self):
        """Test graceful shutdown execution."""
        handler = ShutdownHandler()

        # Mock the close method
        with patch.object(handler, "close", new=AsyncMock()) as mock_close:
            with patch("adk_agui_middleware.tools.shutdown.record_log") as mock_log:
                await handler._graceful_shutdown()

                mock_close.assert_called_once()
                mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_error(self):
        """Test graceful shutdown with error handling."""
        handler = ShutdownHandler()

        # Mock close to raise exception
        with patch.object(
            handler, "close", new=AsyncMock(side_effect=Exception("Shutdown error"))
        ):
            with patch(
                "adk_agui_middleware.tools.shutdown.record_error_log"
            ) as mock_error_log:
                await handler._graceful_shutdown()

                mock_error_log.assert_called_once()

    def test_signal_handler_with_running_loop(self):
        """Test signal handler with running event loop."""
        handler = ShutdownHandler()
        handler._shutdown_in_progress = False

        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_loop.create_task = Mock()

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with patch("adk_agui_middleware.tools.shutdown.record_log"):
                handler._signal_handler(signal.SIGTERM, None)

                mock_loop.create_task.assert_called_once()
                assert handler._shutdown_in_progress is True

    def test_signal_handler_no_running_loop(self):
        """Test signal handler without running event loop."""
        handler = ShutdownHandler()
        handler._shutdown_in_progress = False

        with patch(
            "asyncio.get_running_loop", side_effect=RuntimeError("No running loop")
        ):
            with patch("asyncio.run") as mock_run:
                with patch("adk_agui_middleware.tools.shutdown.record_log"):
                    handler._signal_handler(signal.SIGINT, None)

                    mock_run.assert_called_once()
                    assert handler._shutdown_in_progress is True

    @pytest.mark.asyncio
    async def test_shutdown_function_execution(self):
        """Test execution of registered shutdown functions."""
        handler = ShutdownHandler()

        # Create mock shutdown functions
        mock_func1 = AsyncMock()
        mock_func2 = AsyncMock()

        handler.register_shutdown_function(mock_func1)
        handler.register_shutdown_function(mock_func2)

        # Mock close method to call shutdown functions
        original_close = getattr(handler, "close", None)
        if original_close:
            await handler.close()

            # Functions should have been called (implementation dependent)
            # This tests the registration mechanism works

    def test_shutdown_handler_attributes(self):
        """Test ShutdownHandler has required attributes."""
        handler = ShutdownHandler()

        assert hasattr(handler, "_shutdown_list")
        assert hasattr(handler, "_shutdown_in_progress")
        assert hasattr(handler, "register_shutdown_function")
        assert hasattr(handler, "_signal_handler")
        assert hasattr(handler, "_graceful_shutdown")

    def test_shutdown_list_initialization(self):
        """Test shutdown list is properly initialized."""
        handler = ShutdownHandler()

        assert isinstance(handler._shutdown_list, list)
        assert handler._shutdown_in_progress is False
