# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.event.error_event module."""

import unittest
from unittest.mock import Mock, patch

from ag_ui.core import EventType, RunErrorEvent

from adk_agui_middleware.event.error_event import AGUIErrorEvent


class TestAGUIEncoderError(unittest.TestCase):
    """Test cases for AGUIErrorEvent encoding error methods."""

    @patch("adk_agui_middleware.event.error_event.record_error_log")
    def test_encoding_error(self, mock_record_error):
        """Test creating encoding error event."""
        test_exception = ValueError("Test encoding error")

        result = AGUIErrorEvent.create_encoding_error_event(test_exception)

        self.assertIsInstance(result, RunErrorEvent)
        self.assertEqual(result.type, EventType.RUN_ERROR)
        self.assertIn("Event encoding failed", result.message)
        self.assertEqual(result.code, "ENCODING_ERROR")
        mock_record_error.assert_called_once_with("Event encoding failed", test_exception)

    @patch("adk_agui_middleware.event.error_event.record_error_log")
    def test_agent_error(self, mock_record_error):
        """Test creating agent error event."""
        test_exception = RuntimeError("Test agent error")

        result = AGUIErrorEvent.create_agent_error_event(test_exception)

        self.assertIsInstance(result, RunErrorEvent)
        self.assertEqual(result.type, EventType.RUN_ERROR)
        self.assertIn("Agent execution failed", result.message)
        self.assertEqual(result.code, "AGENT_ERROR")
        mock_record_error.assert_called_once_with("AGUI Agent Error Handler", test_exception)


class TestAGUIErrorEvent(unittest.TestCase):
    """Test cases for AGUIErrorEvent class."""

    @patch("adk_agui_middleware.event.error_event.record_error_log")
    def test_execution_error(self, mock_record_error):
        """Test creating execution error event."""
        test_exception = Exception("Test execution error")
        
        result = AGUIErrorEvent.create_execution_error_event(test_exception)
        
        self.assertIsInstance(result, RunErrorEvent)
        self.assertEqual(result.type, EventType.RUN_ERROR)
        self.assertEqual(result.message, repr(test_exception))
        self.assertEqual(result.code, "EXECUTION_ERROR")
        mock_record_error.assert_called_once_with("Error in new execution", test_exception)

    @patch("adk_agui_middleware.event.error_event.record_error_log")
    def test_no_tool_results(self, mock_record_error):
        """Test creating no tool results error event."""
        thread_id = "test-thread-123"
        
        result = AGUIErrorEvent.create_no_tool_results_error(thread_id)
        
        self.assertIsInstance(result, RunErrorEvent)
        self.assertEqual(result.type, EventType.RUN_ERROR)
        self.assertEqual(result.message, "No tool results found in submission")
        self.assertEqual(result.code, "NO_TOOL_RESULTS")
        mock_record_error.assert_called_once_with(
            f"Tool result submission without tool results for thread {thread_id}"
        )

    @patch("adk_agui_middleware.event.error_event.record_error_log")
    def test_tool_result_processing_error(self, mock_record_error):
        """Test creating tool result processing error event."""
        test_exception = ValueError("Tool processing failed")
        
        result = AGUIErrorEvent.create_tool_processing_error_event(test_exception)
        
        self.assertIsInstance(result, RunErrorEvent)
        self.assertEqual(result.type, EventType.RUN_ERROR)
        self.assertIn("Failed to process tool results", result.message)
        self.assertIn(repr(test_exception), result.message)
        self.assertEqual(result.code, "TOOL_RESULT_PROCESSING_ERROR")
        mock_record_error.assert_called_once_with("Error handling tool results.", test_exception)

    def test_all_error_events_have_run_error_type(self):
        """Test that all error events have RUN_ERROR type."""
        test_exception = Exception("test")
        thread_id = "test-thread"
        
        events = [
            AGUIErrorEvent.create_execution_error_event(test_exception),
            AGUIErrorEvent.create_no_tool_results_error(thread_id),
            AGUIErrorEvent.create_tool_processing_error_event(test_exception),
        ]
        
        for event in events:
            self.assertIsInstance(event, RunErrorEvent)
            self.assertEqual(event.type, EventType.RUN_ERROR)
            self.assertIsNotNone(event.message)
            self.assertIsNotNone(event.code)


if __name__ == "__main__":
    unittest.main()