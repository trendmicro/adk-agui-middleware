"""Unit tests for adk_agui_middleware.tools.shutdown module."""

import asyncio
import signal
import unittest
from unittest.mock import AsyncMock, Mock, patch

from adk_agui_middleware.tools.shutdown import ShutdownHandler


class TestShutdownHandler(unittest.TestCase):
    """Test cases for ShutdownHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear singleton instance for each test
        if hasattr(ShutdownHandler, '_instances'):
            ShutdownHandler._instances.clear()

    @patch('adk_agui_middleware.tools.shutdown.signal.signal')
    def test_init(self, mock_signal):
        """Test ShutdownHandler initialization."""
        handler = ShutdownHandler()
        
        self.assertEqual(handler._shutdown_list, [])
        self.assertFalse(handler._shutdown_in_progress)
        
        # Check that signal handlers were set up
        expected_calls = [
            unittest.mock.call(signal.SIGTERM, handler._signal_handler),
            unittest.mock.call(signal.SIGINT, handler._signal_handler),
            unittest.mock.call(signal.SIGHUP, handler._signal_handler),
        ]
        mock_signal.assert_has_calls(expected_calls, any_order=True)

    def test_singleton_behavior(self):
        """Test that ShutdownHandler follows singleton pattern."""
        handler1 = ShutdownHandler()
        handler2 = ShutdownHandler()
        
        self.assertIs(handler1, handler2)

    def test_register_shutdown_function(self):
        """Test registering shutdown functions."""
        handler = ShutdownHandler()
        
        async def test_shutdown():
            pass
        
        handler.register_shutdown_function(test_shutdown)
        
        self.assertEqual(len(handler._shutdown_list), 1)
        self.assertEqual(handler._shutdown_list[0], test_shutdown)

    def test_register_multiple_shutdown_functions(self):
        """Test registering multiple shutdown functions."""
        handler = ShutdownHandler()
        
        async def shutdown1():
            pass
        
        async def shutdown2():
            pass
        
        handler.register_shutdown_function(shutdown1)
        handler.register_shutdown_function(shutdown2)
        
        self.assertEqual(len(handler._shutdown_list), 2)
        self.assertEqual(handler._shutdown_list[0], shutdown1)
        self.assertEqual(handler._shutdown_list[1], shutdown2)

    @patch('adk_agui_middleware.tools.shutdown.record_log')
    @patch('asyncio.get_running_loop')
    def test_signal_handler_with_running_loop(self, mock_get_loop, mock_record_log):
        """Test signal handler with running event loop."""
        handler = ShutdownHandler()
        
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_get_loop.return_value = mock_loop
        
        handler._signal_handler(signal.SIGTERM, None)
        
        self.assertTrue(handler._shutdown_in_progress)
        mock_record_log.assert_called_once_with(
            f"Received signal {signal.SIGTERM}, initiating graceful shutdown"
        )
        mock_loop.create_task.assert_called_once()

    @patch('adk_agui_middleware.tools.shutdown.record_log')
    @patch('asyncio.get_running_loop')
    def test_signal_handler_loop_not_running(self, mock_get_loop, mock_record_log):
        """Test signal handler when loop is not running."""
        handler = ShutdownHandler()
        
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_get_loop.return_value = mock_loop
        
        with patch('asyncio.run') as mock_asyncio_run:
            handler._signal_handler(signal.SIGTERM, None)
            
            mock_asyncio_run.assert_called_once()

    @patch('adk_agui_middleware.tools.shutdown.record_log')
    @patch('asyncio.get_running_loop')
    def test_signal_handler_no_loop(self, mock_get_loop, mock_record_log):
        """Test signal handler when no event loop exists."""
        handler = ShutdownHandler()
        
        mock_get_loop.side_effect = RuntimeError("No loop")
        
        with patch('asyncio.run') as mock_asyncio_run:
            handler._signal_handler(signal.SIGTERM, None)
            
            mock_asyncio_run.assert_called_once()

    @patch('adk_agui_middleware.tools.shutdown.record_log')
    def test_signal_handler_shutdown_in_progress(self, mock_record_log):
        """Test signal handler when shutdown is already in progress."""
        handler = ShutdownHandler()
        handler._shutdown_in_progress = True
        
        handler._signal_handler(signal.SIGTERM, None)
        
        # Should not log anything when shutdown is already in progress
        mock_record_log.assert_not_called()

    @patch('adk_agui_middleware.tools.shutdown.record_log')
    @patch('adk_agui_middleware.tools.shutdown.record_error_log')
    @patch('asyncio.get_running_loop')
    async def test_graceful_shutdown_success(self, mock_get_loop, mock_record_error, mock_record_log):
        """Test successful graceful shutdown."""
        handler = ShutdownHandler()
        
        mock_shutdown = AsyncMock()
        handler.register_shutdown_function(mock_shutdown)
        
        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop
        
        await handler._graceful_shutdown()
        
        mock_shutdown.assert_called_once()
        mock_record_log.assert_called_with("Shutdown functions completed successfully")
        mock_loop.call_later.assert_called_once_with(1, mock_loop.stop)

    @patch('adk_agui_middleware.tools.shutdown.record_log')
    @patch('adk_agui_middleware.tools.shutdown.record_error_log')
    @patch('asyncio.get_running_loop')
    async def test_graceful_shutdown_with_error(self, mock_get_loop, mock_record_error, mock_record_log):
        """Test graceful shutdown with error in close()."""
        handler = ShutdownHandler()
        
        # Mock close to raise an exception
        with patch.object(handler, 'close', side_effect=Exception("Test error")):
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop
            
            await handler._graceful_shutdown()
            
            mock_record_error.assert_called_once()
            mock_loop.call_later.assert_called_once_with(1, mock_loop.stop)

    @patch('adk_agui_middleware.tools.shutdown.record_log')
    @patch('adk_agui_middleware.tools.shutdown.record_error_log')
    @patch('asyncio.get_running_loop')
    async def test_graceful_shutdown_no_loop_finally(self, mock_get_loop, mock_record_error, mock_record_log):
        """Test graceful shutdown when no loop in finally block."""
        handler = ShutdownHandler()
        
        mock_get_loop.side_effect = RuntimeError("No loop")
        
        await handler._graceful_shutdown()
        
        # Should not raise an exception

    @patch('adk_agui_middleware.tools.shutdown.record_error_log')
    async def test_close_success(self, mock_record_error):
        """Test successful close operation."""
        handler = ShutdownHandler()
        
        mock_shutdown1 = AsyncMock()
        mock_shutdown2 = AsyncMock()
        
        handler.register_shutdown_function(mock_shutdown1)
        handler.register_shutdown_function(mock_shutdown2)
        
        await handler.close()
        
        mock_shutdown1.assert_called_once()
        mock_shutdown2.assert_called_once()
        mock_record_error.assert_not_called()

    @patch('adk_agui_middleware.tools.shutdown.record_error_log')
    async def test_close_with_error(self, mock_record_error):
        """Test close operation with error in shutdown function."""
        handler = ShutdownHandler()
        
        async def failing_shutdown():
            raise Exception("Shutdown error")
        
        mock_working_shutdown = AsyncMock()
        
        handler.register_shutdown_function(failing_shutdown)
        handler.register_shutdown_function(mock_working_shutdown)
        
        await handler.close()
        
        # Should continue even with error
        mock_working_shutdown.assert_called_once()
        mock_record_error.assert_called_once()

    @patch('adk_agui_middleware.tools.shutdown.record_error_log')
    async def test_close_multiple_errors(self, mock_record_error):
        """Test close operation with multiple errors."""
        handler = ShutdownHandler()
        
        async def failing_shutdown1():
            raise Exception("Error 1")
        
        async def failing_shutdown2():
            raise Exception("Error 2")
        
        handler.register_shutdown_function(failing_shutdown1)
        handler.register_shutdown_function(failing_shutdown2)
        
        await handler.close()
        
        # Should log both errors
        self.assertEqual(mock_record_error.call_count, 2)

    def test_setup_signal_handlers(self):
        """Test signal handler setup."""
        with patch('adk_agui_middleware.tools.shutdown.signal.signal') as mock_signal:
            handler = ShutdownHandler()
            
            # Verify all expected signals are handled
            signal_calls = [call[0][0] for call in mock_signal.call_args_list]
            self.assertIn(signal.SIGTERM, signal_calls)
            self.assertIn(signal.SIGINT, signal_calls)
            self.assertIn(signal.SIGHUP, signal_calls)


if __name__ == "__main__":
    unittest.main()