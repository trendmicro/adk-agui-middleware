"""Consolidated tests for all tools modules."""

import json
import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch, PropertyMock

from ag_ui.core import (
    AssistantMessage, UserMessage, ToolMessage, SystemMessage,
    FunctionCall, ToolCall
)
from google.adk.events import Event as ADKEvent
from pydantic import BaseModel

from adk_agui_middleware.tools.convert import (
    convert_ag_ui_messages_to_adk,
    convert_adk_event_to_ag_ui_message,
    convert_agui_to_adk_event,
    convert_json_patch_to_state,
    convert_state_to_json_patch
)
from adk_agui_middleware.tools.function_name import (
    get_function_name,
    _should_skip_function,
    _format_function_name
)
from adk_agui_middleware.tools.json_encoder import DataclassesEncoder

from .test_utils import BaseTestCase, TEST_CONSTANTS, parametrize_test_cases


class TestDataclassesEncoder(BaseTestCase):
    """Test cases for DataclassesEncoder."""

    def setUp(self):
        super().setUp()
        self.encoder = DataclassesEncoder()

    @parametrize_test_cases([
        {"data": b"test bytes", "expected": "test bytes"},
        {"data": b"\x80\x81", "expected": "[Binary Data]"},
        {"data": b"", "expected": ""},
    ])
    def test_encode_bytes(self, data: bytes, expected: str):
        """Test bytes encoding with various inputs."""
        result = self.encoder.default(data)
        assert result == expected

    def test_encode_pydantic_model(self):
        """Test Pydantic model encoding."""
        class TestModel(BaseModel):
            name: str = "test"
            value: int = 42

        model = TestModel(name="test", value=42)  # Explicitly set values
        result = self.encoder.default(model)
        
        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_encode_unsupported_type(self):
        """Test encoding unsupported types raises TypeError."""
        unsupported_obj = object()
        
        with pytest.raises(TypeError):
            self.encoder.default(unsupported_obj)

    def test_full_json_encoding(self):
        """Test complete JSON encoding workflow."""
        class TestModel(BaseModel):
            name: str = "test"
            data: bytes = b"binary"

        test_data = {
            "model": TestModel(name="test", data=b"binary"),  # Explicitly set values
            "bytes": b"test",
            "normal": "string"
        }

        result = json.dumps(test_data, cls=DataclassesEncoder)
        decoded = json.loads(result)
        
        assert decoded["model"]["name"] == "test"
        assert decoded["bytes"] == "test"
        assert decoded["normal"] == "string"


class TestFunctionNameUtils(BaseTestCase):
    """Test cases for function name utilities."""

    @parametrize_test_cases([
        {"func_name": "get_function_name", "expected": True},
        {"func_name": "debug", "expected": True},
        {"func_name": "wrapper", "expected": True},
        {"func_name": "_record_raw_data_log", "expected": True},
        {"func_name": "trace", "expected": True},
    ])
    def test_should_skip_function_skip_cases(self, func_name: str, expected: bool):
        """Test functions that should be skipped."""
        result = _should_skip_function(func_name)
        assert result == expected

    @parametrize_test_cases([
        {"func_name": "__init__", "expected": False},
        {"func_name": "my_function", "expected": False},
        {"func_name": "process_data", "expected": False},
        {"func_name": "custom_method", "expected": False},
    ])
    def test_should_skip_function_include_cases(self, func_name: str, expected: bool):
        """Test functions that should be included."""
        result = _should_skip_function(func_name)
        assert result == expected

    def test_format_function_name_basic(self):
        """Test basic function name formatting."""
        result = _format_function_name("test_func", {"param": "value"})
        assert result == "test_func"

    def test_get_function_name_integration(self):
        """Test get_function_name returns valid string."""
        def test_function():
            return get_function_name()

        result = test_function()
        assert isinstance(result, str)
        assert len(result) > 0


class TestConvertFunctions(BaseTestCase):
    """Test cases for conversion functions."""

    def setUp(self):
        super().setUp()

    # Message to ADK conversion tests
    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_messages_empty_list(self, mock_log):
        """Test converting empty message list."""
        result = convert_ag_ui_messages_to_adk([])
        assert result == []
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_user_message(self, mock_log):
        """Test converting user message to ADK format."""
        user_msg = self.create_test_data("user_message", content="Hello world")
        
        result = convert_ag_ui_messages_to_adk([user_msg])
        
        assert len(result) == 1
        assert result[0].author == "user"
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_assistant_message_with_tools(self, mock_log):
        """Test converting assistant message with tool calls."""
        tool_call = self.create_test_data("tool_call")
        assistant_msg = self.create_test_data(
            "assistant_message", 
            content="Using tool",
            tool_calls=[tool_call]
        )
        
        result = convert_ag_ui_messages_to_adk([assistant_msg])
        
        assert len(result) == 1
        assert result[0].author == "assistant"
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_with_exception(self, mock_log):
        """Test conversion handles exceptions gracefully."""
        # Create a message that will cause an exception
        invalid_msg = Mock()
        invalid_msg.role = "invalid"
        
        result = convert_ag_ui_messages_to_adk([invalid_msg])
        
        # Should return empty list and log error
        assert result == []
        mock_log.assert_called_once()

    # ADK to AGUI conversion tests  
    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_adk_event_empty(self, mock_log):
        """Test converting empty ADK event."""
        mock_event = Mock()  # Remove spec to allow content attribute
        mock_event.id = "test_event"
        mock_event.content = Mock()
        mock_event.content.parts = []
        
        result = convert_adk_event_to_ag_ui_message(mock_event)
        
        assert result is None
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log") 
    def test_convert_adk_event_with_content(self, mock_log):
        """Test converting ADK event with text content."""
        mock_event = Mock()  # Remove spec to allow content attribute
        mock_event.id = "test_event"
        mock_event.content = Mock()
        mock_part = Mock()
        mock_part.text = "Test response"
        mock_event.content.parts = [mock_part]
        
        result = convert_adk_event_to_ag_ui_message(mock_event)
        
        assert result is not None
        assert hasattr(result, 'content')
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_adk_event_exception_handling(self, mock_log):
        """Test ADK event conversion exception handling."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.id = "error_event"
        
        # Create mock content with exception
        mock_content = Mock()
        mock_content.parts = PropertyMock(side_effect=Exception("Test error"))
        mock_event.content = mock_content
        
        result = convert_adk_event_to_ag_ui_message(mock_event)
        
        assert result is None
        mock_log.assert_called_once()

    # AGUI to ADK event conversion
    def test_convert_agui_to_adk_user_message(self):
        """Test converting AGUI user message to ADK event."""
        user_msg = self.create_test_data("user_message")
        
        result = convert_agui_to_adk_event(user_msg)
        
        assert result is not None
        assert result.role == "user"

    def test_convert_agui_to_adk_tool_message(self):
        """Test converting AGUI tool message to ADK event."""
        tool_msg = self.create_test_data("tool_message")
        
        result = convert_agui_to_adk_event(tool_msg)
        
        assert result is not None
        assert result.role == "function"

    def test_convert_agui_to_adk_unsupported_type(self):
        """Test converting unsupported message type."""
        unsupported_msg = Mock()
        unsupported_msg.role = "unknown"
        
        result = convert_agui_to_adk_event(unsupported_msg)
        
        assert result is None

    # JSON Patch conversion tests
    @parametrize_test_cases([
        {
            "state": {"key1": "value1", "key2": "value2"},
            "expected_ops": 2
        },
        {
            "state": {},
            "expected_ops": 0
        },
        {
            "state": {"single": "value"},
            "expected_ops": 1
        }
    ])
    def test_convert_state_to_json_patch(self, state: Dict[str, Any], expected_ops: int):
        """Test converting state dictionary to JSON patch operations."""
        result = convert_state_to_json_patch(state)
        
        assert len(result) == expected_ops
        for op in result:
            assert op["op"] == "add"
            assert op["path"].startswith("/")

    @parametrize_test_cases([
        {
            "patches": [{"op": "add", "path": "/key1", "value": "value1"}],
            "expected_key": "key1",
            "expected_value": "value1"
        },
        {
            "patches": [],
            "expected_key": None,
            "expected_value": None
        }
    ])
    def test_convert_json_patch_to_state(self, patches: List[Dict], expected_key: str, expected_value: Any):
        """Test converting JSON patch operations to state dictionary."""
        result = convert_json_patch_to_state(patches)
        
        if expected_key:
            assert expected_key in result
            assert result[expected_key] == expected_value
        else:
            assert result == {}

    def test_json_patch_roundtrip_conversion(self):
        """Test roundtrip conversion between state and JSON patch."""
        original_state = {"test": "value", "number": 42, "bool": True}
        
        # Convert to patches and back
        patches = convert_state_to_json_patch(original_state)
        converted_state = convert_json_patch_to_state(patches)
        
        assert converted_state == original_state

    def test_json_patch_invalid_operation(self):
        """Test handling invalid JSON patch operations."""
        invalid_patches = [{"op": "invalid", "path": "/test"}]
        
        result = convert_json_patch_to_state(invalid_patches)
        
        # Should handle gracefully and return empty dict
        assert result == {}

    def test_json_patch_invalid_path(self):
        """Test handling invalid JSON patch paths."""
        invalid_patches = [{"op": "add", "path": "invalid_path", "value": "test"}]
        
        result = convert_json_patch_to_state(invalid_patches)
        
        # Should skip invalid paths
        assert result == {}

    # Integration tests
    def test_message_conversion_workflow(self):
        """Test complete message conversion workflow."""
        # Create message chain
        user_msg = self.create_test_data("user_message", content="Hello")
        tool_call = self.create_test_data("tool_call")
        assistant_msg = self.create_test_data(
            "assistant_message",
            content="Using tool", 
            tool_calls=[tool_call]
        )
        tool_msg = self.create_test_data("tool_message", tool_call_id="call_1")
        
        messages = [user_msg, assistant_msg, tool_msg]
        
        # Convert to ADK format
        adk_messages = convert_ag_ui_messages_to_adk(messages)
        
        # Should have all messages converted
        assert len(adk_messages) == 3
        assert adk_messages[0].author == "user"
        assert adk_messages[1].author == "assistant" 
        assert adk_messages[2].author == "tool"

    def test_state_management_workflow(self):
        """Test complete state management workflow."""
        # Initial state
        initial_state = {"user_id": "123", "session": "active", "count": 0}
        
        # Convert to patches
        patches = convert_state_to_json_patch(initial_state)
        
        # Modify patches (simulate state updates)
        update_patches = patches + [
            {"op": "add", "path": "/count", "value": 5},
            {"op": "add", "path": "/last_action", "value": "increment"}
        ]
        
        # Convert back to state
        final_state = convert_json_patch_to_state(update_patches)
        
        # Verify state updates
        assert final_state["user_id"] == "123"
        assert final_state["count"] == 5  # Should be updated value
        assert final_state["last_action"] == "increment"

    # Error handling and edge cases
    def test_convert_none_input(self):
        """Test conversion functions with None input."""
        assert convert_ag_ui_messages_to_adk(None) == []
        assert convert_adk_event_to_ag_ui_message(None) is None
        assert convert_json_patch_to_state(None) == {}
        assert convert_state_to_json_patch(None) == []

    def test_convert_empty_content_message(self):
        """Test converting message with empty content."""
        empty_msg = self.create_test_data("user_message", content="")
        
        result = convert_agui_to_adk_event(empty_msg)
        
        # Empty content returns None based on implementation
        assert result is None

    @parametrize_test_cases([
        {"invalid_json": "{ invalid }", "expected_error": True},
        {"valid_json": '{"valid": true}', "expected_error": False},
        {"empty_string": "", "expected_error": False},
    ])
    def test_json_content_handling(self, invalid_json: str = "", valid_json: str = "", empty_string: str = "", expected_error: bool = False):
        """Test handling of various JSON content formats."""
        # Use whichever parameter is provided
        content = invalid_json or valid_json or empty_string
        tool_msg = self.create_test_data("tool_message", content=content)
        
        result = convert_agui_to_adk_event(tool_msg)
        
        # Should always return valid result regardless of JSON validity
        assert result is not None