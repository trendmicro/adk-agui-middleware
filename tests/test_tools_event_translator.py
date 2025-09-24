# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.tools.event_translator module."""

import asyncio
import json
import unittest
import uuid
from unittest.mock import AsyncMock, Mock, patch

from ag_ui.core import (BaseEvent, CustomEvent, EventType, StateDeltaEvent,
                        StateSnapshotEvent, TextMessageContentEvent,
                        TextMessageEndEvent, TextMessageStartEvent,
                        ToolCallArgsEvent, ToolCallEndEvent,
                        ToolCallResultEvent, ToolCallStartEvent)
from google.adk.events import Event as ADKEvent
from google.genai import types

from adk_agui_middleware.event.event_translator import EventTranslator


class TestEventTranslator(unittest.TestCase):
    """Test cases for EventTranslator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.translator = EventTranslator()

    def test_init(self):
        """Test EventTranslator initialization."""
        self.assertEqual(self.translator._streaming_message_id, {})
        self.assertEqual(self.translator.long_running_tool_ids, {})

    @patch("adk_agui_middleware.tools.event_translator.record_error_log")
    async def test_translate_user_authored_event(self, mock_record_error):
        """Test that user-authored events are skipped."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.author = "user"
        
        events = []
        async for event in self.translator.translate(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 0)
        mock_record_error.assert_not_called()

    @patch("adk_agui_middleware.tools.event_translator.record_error_log")
    async def test_translate_exception_handling(self, mock_record_error):
        """Test exception handling during translation."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.author = "agent"
        mock_event.content = None
        mock_event.get_function_calls.side_effect = Exception("Test error")
        mock_event.get_function_responses.return_value = []
        
        events = []
        async for event in self.translator.translate(mock_event):
            events.append(event)
        
        mock_record_error.assert_called_once()

    async def test_translate_text_content_start_streaming(self):
        """Test starting text content streaming."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.author = "agent"
        mock_event.content = Mock()
        mock_part = Mock()
        mock_part.text = "Hello"
        mock_event.content.parts = [mock_part]
        mock_event.is_final_response.return_value = False
        mock_event.get_function_calls.return_value = []
        mock_event.get_function_responses.return_value = []
        mock_event.actions = None
        mock_event.custom_metadata = None
        
        events = []
        async for event in self.translator.translate(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 2)
        self.assertIsInstance(events[0], TextMessageStartEvent)
        self.assertIsInstance(events[1], TextMessageContentEvent)
        self.assertEqual(events[0].role, "assistant")
        self.assertEqual(events[1].delta, "Hello")
        self.assertTrue(self.translator._is_streaming)
        self.assertIsNotNone(self.translator._streaming_message_id)

    async def test_translate_text_content_end_streaming(self):
        """Test ending text content streaming."""
        # First start streaming
        self.translator._is_streaming = True
        self.translator._streaming_message_id = "test-id"
        
        mock_event = Mock(spec=ADKEvent)
        mock_event.author = "agent"
        mock_event.content = Mock()
        mock_part = Mock()
        mock_part.text = "World"
        mock_event.content.parts = [mock_part]
        mock_event.is_final_response.return_value = True
        mock_event.get_function_calls.return_value = []
        mock_event.get_function_responses.return_value = []
        mock_event.actions = None
        mock_event.custom_metadata = None
        
        events = []
        async for event in self.translator.translate(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 2)
        self.assertIsInstance(events[0], TextMessageContentEvent)
        self.assertIsInstance(events[1], TextMessageEndEvent)
        self.assertEqual(events[0].delta, "World")
        self.assertFalse(self.translator._is_streaming)
        self.assertIsNone(self.translator._streaming_message_id)

    async def test_translate_text_content_no_text_parts(self):
        """Test handling content with no text parts."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.author = "agent"
        mock_event.content = Mock()
        mock_part = Mock()
        mock_part.text = None
        mock_event.content.parts = [mock_part]
        mock_event.get_function_calls.return_value = []
        mock_event.get_function_responses.return_value = []
        mock_event.actions = None
        mock_event.custom_metadata = None
        
        events = []
        async for event in self.translator.translate(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 0)

    async def test_translate_text_content_none_content(self):
        """Test handling event with None content."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.author = "agent"
        mock_event.content = None
        mock_event.get_function_calls.return_value = []
        mock_event.get_function_responses.return_value = []
        mock_event.actions = None
        mock_event.custom_metadata = None
        
        events = []
        async for event in self.translator.translate(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 0)

    async def test_translate_function_calls(self):
        """Test translating function calls."""
        mock_func_call = Mock(spec=types.FunctionCall)
        mock_func_call.id = "call-123"
        mock_func_call.name = "test_function"
        mock_func_call.args = {"param": "value"}
        
        events = []
        async for event in self.translator.translate_function_calls([mock_func_call]):
            events.append(event)
        
        self.assertEqual(len(events), 3)
        self.assertIsInstance(events[0], ToolCallStartEvent)
        self.assertIsInstance(events[1], ToolCallArgsEvent)
        self.assertIsInstance(events[2], ToolCallEndEvent)
        
        self.assertEqual(events[0].tool_call_id, "call-123")
        self.assertEqual(events[0].tool_call_name, "test_function")
        self.assertEqual(events[1].tool_call_id, "call-123")
        self.assertEqual(events[1].delta, '{"param": "value"}')
        self.assertEqual(events[2].tool_call_id, "call-123")

    async def test_translate_function_calls_no_id(self):
        """Test translating function calls without ID."""
        mock_func_call = Mock(spec=types.FunctionCall)
        mock_func_call.id = None
        mock_func_call.name = "test_function"
        mock_func_call.args = None
        
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="generated-id")
            
            events = []
            async for event in self.translator.translate_function_calls([mock_func_call]):
                events.append(event)
        
        self.assertEqual(len(events), 2)  # No args event when args is None
        self.assertIsInstance(events[0], ToolCallStartEvent)
        self.assertIsInstance(events[1], ToolCallEndEvent)
        self.assertEqual(events[0].tool_call_id, "generated-id")

    async def test_translate_function_calls_string_args(self):
        """Test translating function calls with string args."""
        mock_func_call = Mock(spec=types.FunctionCall)
        mock_func_call.id = "call-123"
        mock_func_call.name = "test_function"
        mock_func_call.args = "string_args"
        
        events = []
        async for event in self.translator.translate_function_calls([mock_func_call]):
            events.append(event)
        
        self.assertEqual(len(events), 3)
        self.assertIsInstance(events[1], ToolCallArgsEvent)
        self.assertEqual(events[1].delta, "string_args")

    async def test_translate_function_response(self):
        """Test translating function responses."""
        mock_func_response = Mock(spec=types.FunctionResponse)
        mock_func_response.id = "response-123"
        mock_func_response.response = {"result": "success"}
        
        events = []
        async for event in self.translator.translate_function_response([mock_func_response]):
            events.append(event)
        
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], ToolCallResultEvent)
        self.assertEqual(events[0].tool_call_id, "response-123")
        self.assertEqual(events[0].content, '{"result": "success"}')

    @patch("adk_agui_middleware.tools.event_translator.record_debug_log")
    async def test_translate_function_response_long_running(self, mock_debug_log):
        """Test translating function responses for long-running tools."""
        self.translator.long_running_tool_ids = ["response-123"]
        
        mock_func_response = Mock(spec=types.FunctionResponse)
        mock_func_response.id = "response-123"
        mock_func_response.response = {"result": "success"}
        
        events = []
        async for event in self.translator.translate_function_response([mock_func_response]):
            events.append(event)
        
        self.assertEqual(len(events), 0)
        mock_debug_log.assert_called_once()

    async def test_translate_function_response_no_id(self):
        """Test translating function responses without ID."""
        mock_func_response = Mock(spec=types.FunctionResponse)
        mock_func_response.id = None
        mock_func_response.response = {"result": "success"}
        
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="generated-id")
            
            events = []
            async for event in self.translator.translate_function_response([mock_func_response]):
                events.append(event)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].tool_call_id, "generated-id")

    async def test_translate_lro_function_calls(self):
        """Test translating long-running operation function calls."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.content = Mock()
        mock_part = Mock()
        mock_part.function_call = Mock()
        mock_part.function_call.id = "lro-123"
        mock_part.function_call.name = "long_running_func"
        mock_part.function_call.args = {"timeout": 300}
        mock_event.content.parts = [mock_part]
        mock_event.long_running_tool_ids = ["lro-123"]
        
        events = []
        async for event in self.translator.translate_lro_function_calls(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 3)
        self.assertIsInstance(events[0], ToolCallStartEvent)
        self.assertIsInstance(events[1], ToolCallArgsEvent)
        self.assertIsInstance(events[2], ToolCallEndEvent)
        self.assertIn("lro-123", self.translator.long_running_tool_ids)

    async def test_translate_lro_function_calls_no_content(self):
        """Test LRO function calls with no content."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.content = None
        
        events = []
        async for event in self.translator.translate_lro_function_calls(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 0)

    async def test_translate_lro_function_calls_not_lro(self):
        """Test function calls that are not long-running."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.content = Mock()
        mock_part = Mock()
        mock_part.function_call = Mock()
        mock_part.function_call.id = "regular-123"
        mock_part.function_call.name = "regular_func"
        mock_event.content.parts = [mock_part]
        mock_event.long_running_tool_ids = ["other-id"]
        
        events = []
        async for event in self.translator.translate_lro_function_calls(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 0)

    async def test_handle_additional_data_state_delta(self):
        """Test handling state delta data."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.actions = Mock()
        mock_event.actions.state_delta = {"key": "value"}
        mock_event.custom_metadata = None
        
        events = []
        async for event in self.translator._handle_additional_data(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], StateDeltaEvent)

    async def test_handle_additional_data_custom_metadata(self):
        """Test handling custom metadata."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.actions = None
        mock_event.custom_metadata = {"custom": "data"}
        
        events = []
        async for event in self.translator._handle_additional_data(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], CustomEvent)
        self.assertEqual(events[0].name, "adk_custom_metadata")
        self.assertEqual(events[0].value, {"custom": "data"})

    async def test_handle_additional_data_both(self):
        """Test handling both state delta and custom metadata."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.actions = Mock()
        mock_event.actions.state_delta = {"key": "value"}
        mock_event.custom_metadata = {"custom": "data"}
        
        events = []
        async for event in self.translator._handle_additional_data(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 2)
        self.assertIsInstance(events[0], StateDeltaEvent)
        self.assertIsInstance(events[1], CustomEvent)

    def test_create_state_delta_event(self):
        """Test creating state delta event."""
        state_delta = {"key1": "value1", "key2": "value2"}
        event = self.translator.create_state_delta_event(state_delta)
        
        self.assertIsInstance(event, StateDeltaEvent)
        self.assertEqual(event.type, EventType.STATE_DELTA)
        expected_patches = [
            {"op": "add", "path": "/key1", "value": "value1"},
            {"op": "add", "path": "/key2", "value": "value2"}
        ]
        self.assertEqual(event.delta, expected_patches)

    def test_create_state_snapshot_event(self):
        """Test creating state snapshot event."""
        state_snapshot = {"complete": "state", "data": 123}
        event = self.translator.create_state_snapshot_event(state_snapshot)
        
        self.assertIsInstance(event, StateSnapshotEvent)
        self.assertEqual(event.type, EventType.STATE_SNAPSHOT)
        self.assertEqual(event.snapshot, state_snapshot)

    @patch("adk_agui_middleware.tools.event_translator.record_warning_log")
    async def test_force_close_streaming_message(self, mock_warning_log):
        """Test force closing streaming message."""
        self.translator._is_streaming = True
        self.translator._streaming_message_id = "test-stream-id"
        
        events = []
        async for event in self.translator.force_close_streaming_message():
            events.append(event)
        
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TextMessageEndEvent)
        self.assertEqual(events[0].message_id, "test-stream-id")
        self.assertFalse(self.translator._is_streaming)
        self.assertIsNone(self.translator._streaming_message_id)
        mock_warning_log.assert_called_once()

    async def test_force_close_streaming_message_not_streaming(self):
        """Test force closing when not streaming."""
        self.translator._is_streaming = False
        self.translator._streaming_message_id = None
        
        events = []
        async for event in self.translator.force_close_streaming_message():
            events.append(event)
        
        self.assertEqual(len(events), 0)

    async def test_handle_function_calls(self):
        """Test handling function calls with streaming closure."""
        # Set up streaming state
        self.translator._is_streaming = True
        self.translator._streaming_message_id = "stream-id"
        
        mock_event = Mock(spec=ADKEvent)
        mock_func_call = Mock(spec=types.FunctionCall)
        mock_func_call.id = "call-123"
        mock_func_call.name = "test_function"
        mock_func_call.args = None
        mock_event.get_function_calls.return_value = [mock_func_call]
        
        events = []
        async for event in self.translator._handle_function_calls(mock_event):
            events.append(event)
        
        # Should have end event + tool call events
        self.assertGreater(len(events), 1)
        self.assertIsInstance(events[0], TextMessageEndEvent)
        self.assertFalse(self.translator._is_streaming)

    async def test_translate_streaming_message_content_with_text_streaming(self):
        """Test translating streaming message with text when already streaming."""
        # Set up streaming state
        self.translator._is_streaming = True
        self.translator._streaming_message_id = "existing-stream"
        
        mock_part = Mock()
        mock_part.text = "Additional text"
        
        events = []
        async for event in self.translator.translate_streaming_message_content([mock_part]):
            events.append(event)
        
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TextMessageContentEvent)
        self.assertEqual(events[0].delta, "Additional text")

    async def test_translate_message_non_streaming_pattern(self):
        """Test translating message with non-streaming pattern."""
        # Mock the get_default_message_translation_pattern to return non-streaming
        with patch.object(self.translator, 'get_default_message_translation_pattern', 
                         return_value=asyncio.coroutine(lambda: "complete")()):
            mock_part = Mock()
            mock_part.text = "Complete message"
            
            mock_message = Mock()
            mock_message.id = "msg-456"
            mock_message.parts = [mock_part]
            mock_message.role = "model"
            
            events = []
            async for event in self.translator.translate_message(mock_message):
                events.append(event)
            
            # Should generate complete message events
            self.assertGreater(len(events), 0)

    async def test_translate_streaming_message_content_part_without_attributes(self):
        """Test translating streaming message part with no recognized attributes."""
        mock_part = Mock()
        # Remove all recognized attributes
        if hasattr(mock_part, 'text'):
            delattr(mock_part, 'text')
        if hasattr(mock_part, 'function_call'):
            delattr(mock_part, 'function_call')
        if hasattr(mock_part, 'function_response'):
            delattr(mock_part, 'function_response')
        
        events = []
        async for event in self.translator.translate_streaming_message_content([mock_part]):
            events.append(event)
        
        # Should not generate any events
        self.assertEqual(len(events), 0)

    async def test_handle_additional_data_no_data(self):
        """Test handling additional data when no data present."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.actions = None
        mock_event.custom_metadata = None
        
        events = []
        async for event in self.translator._handle_additional_data(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 0)

    async def test_handle_additional_data_empty_state_delta(self):
        """Test handling empty state delta."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.actions = Mock()
        mock_event.actions.state_delta = {}
        mock_event.custom_metadata = None
        
        events = []
        async for event in self.translator._handle_additional_data(mock_event):
            events.append(event)
        
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], StateDeltaEvent)
        self.assertEqual(events[0].delta, [])


if __name__ == "__main__":
    unittest.main()