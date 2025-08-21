"""Unit tests for adk_agui_middleware.event.error_event module."""

import unittest
from unittest.mock import Mock, patch

from ag_ui.core import EventType, RunErrorEvent

from adk_agui_middleware.event.error_event import AGUIEncoderError, AGUIErrorEvent


class TestAGUIEncoderError(unittest.TestCase):
    """Test cases for AGUIEncoderError class."""

    @patch("adk_agui_middleware.event.error_event.record_error_log")
    @patch("adk_agui_middleware.event.error_event.agui_to_sse")
    def test_encoding_error(self, mock_agui_to_sse, mock_record_error):
        """Test creating encoding error event."""
        test_exception = ValueError("Test encoding error")
        mock_agui_to_sse.return_value = {"event": "error", "data": "test"}
        
        result = AGUIEncoderError.encoding_error(test_exception)
        
        self.assertEqual(result, {"event": "error", "data": "test"})
        mock_record_error.assert_called_once_with("Event encoding failed", test_exception)
        mock_agui_to_sse.assert_called_once()
        
        # Check the RunErrorEvent that was passed to agui_to_sse
        call_args = mock_agui_to_sse.call_args[0][0]
        self.assertIsInstance(call_args, RunErrorEvent)
        self.assertEqual(call_args.type, EventType.RUN_ERROR)
        self.assertIn("Event encoding failed", call_args.message)
        self.assertEqual(call_args.code, "ENCODING_ERROR")

    @patch("adk_agui_middleware.event.error_event.record_error_log")
    @patch("adk_agui_middleware.event.error_event.agui_to_sse")
    def test_agent_error(self, mock_agui_to_sse, mock_record_error):
        """Test creating agent error event."""
        test_exception = RuntimeError("Test agent error")
        mock_agui_to_sse.return_value = {"event": "error", "data": "agent_error"}
        
        result = AGUIEncoderError.agent_error(test_exception)
        
        self.assertEqual(result, {"event": "error", "data": "agent_error"})
        mock_record_error.assert_called_once_with("AGUI Agent Error Handler", test_exception)
        mock_agui_to_sse.assert_called_once()
        
        # Check the RunErrorEvent that was passed to agui_to_sse
        call_args = mock_agui_to_sse.call_args[0][0]
        self.assertIsInstance(call_args, RunErrorEvent)
        self.assertEqual(call_args.type, EventType.RUN_ERROR)
        self.assertIn("Agent execution failed", call_args.message)
        self.assertEqual(call_args.code, "AGENT_ERROR")


class TestAGUIErrorEvent(unittest.TestCase):
    """Test cases for AGUIErrorEvent class."""

    @patch("adk_agui_middleware.event.error_event.record_error_log")
    def test_execution_error(self, mock_record_error):
        """Test creating execution error event."""
        test_exception = Exception("Test execution error")
        
        result = AGUIErrorEvent.execution_error(test_exception)
        
        self.assertIsInstance(result, RunErrorEvent)
        self.assertEqual(result.type, EventType.RUN_ERROR)
        self.assertEqual(result.message, repr(test_exception))
        self.assertEqual(result.code, "EXECUTION_ERROR")
        mock_record_error.assert_called_once_with("Error in new execution", test_exception)

    @patch("adk_agui_middleware.event.error_event.record_error_log")
    def test_no_tool_results(self, mock_record_error):
        """Test creating no tool results error event."""
        thread_id = "test-thread-123"
        
        result = AGUIErrorEvent.no_tool_results(thread_id)
        
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
        
        result = AGUIErrorEvent.tool_result_processing_error(test_exception)
        
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
            AGUIErrorEvent.execution_error(test_exception),
            AGUIErrorEvent.no_tool_results(thread_id),
            AGUIErrorEvent.tool_result_processing_error(test_exception),
        ]
        
        for event in events:
            self.assertIsInstance(event, RunErrorEvent)
            self.assertEqual(event.type, EventType.RUN_ERROR)
            self.assertIsNotNone(event.message)
            self.assertIsNotNone(event.code)


if __name__ == "__main__":
    unittest.main()