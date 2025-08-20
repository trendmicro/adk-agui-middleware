"""Unit tests for adk_agui_middleware.tools.convert module."""

import unittest
from unittest.mock import Mock, patch

from ag_ui.core import BaseEvent, EventType

from adk_agui_middleware.tools.convert import agui_to_sse


class TestAGUIToSSE(unittest.TestCase):
    """Test cases for agui_to_sse function."""

    @patch('time.time')
    def test_basic_conversion(self, mock_time):
        """Test basic AGUI to SSE conversion."""
        mock_time.return_value = 1234567890.123
        
        # Create a mock BaseEvent
        mock_event = Mock(spec=BaseEvent)
        mock_event.type = Mock()
        mock_event.type.value = "test_event_type"
        mock_event.model_dump_json.return_value = '{"test": "data"}'
        
        result = agui_to_sse(mock_event)
        
        self.assertIsInstance(result, dict)
        self.assertIn("data", result)
        self.assertIn("event", result)
        self.assertIn("id", result)
        self.assertEqual(result["event"], "test_event_type")
        self.assertEqual(result["data"], '{"test": "data"}')
        
        # Verify timestamp was set
        self.assertEqual(mock_event.timestamp, 1234567890123)

    def test_conversion_with_real_event_type(self):
        """Test conversion with real EventType enum."""
        mock_event = Mock(spec=BaseEvent)
        mock_event.type = EventType.TEXT_MESSAGE_START
        mock_event.model_dump_json.return_value = '{"message": "hello"}'
        
        result = agui_to_sse(mock_event)
        
        self.assertEqual(result["event"], "TEXT_MESSAGE_START")
        self.assertEqual(result["data"], '{"message": "hello"}')

    def test_model_dump_json_called_correctly(self):
        """Test that model_dump_json is called with correct parameters."""
        mock_event = Mock(spec=BaseEvent)
        mock_event.type = Mock()
        mock_event.type.value = "test"
        mock_event.model_dump_json.return_value = '{}'
        
        agui_to_sse(mock_event)
        
        # Verify model_dump_json was called with correct parameters
        mock_event.model_dump_json.assert_called_once_with(
            by_alias=True, exclude_none=True, exclude={"type"}
        )

    def test_unique_id_generation(self):
        """Test that each call generates a unique ID."""
        mock_event = Mock(spec=BaseEvent)
        mock_event.type = Mock()
        mock_event.type.value = "test"
        mock_event.model_dump_json.return_value = '{}'
        
        result1 = agui_to_sse(mock_event)
        result2 = agui_to_sse(mock_event)
        
        self.assertNotEqual(result1["id"], result2["id"])


if __name__ == "__main__":
    unittest.main()