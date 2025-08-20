"""Consolidated tests for all tools modules."""

import json
from unittest.mock import Mock, patch

import pytest
from ag_ui.core import BaseEvent, EventType
from pydantic import BaseModel

from adk_agui_middleware.tools.convert import agui_to_sse
from adk_agui_middleware.tools.function_name import (
    _format_function_name,
    _should_skip_function,
    get_function_name,
)
from adk_agui_middleware.tools.json_encoder import DataclassesEncoder

from .test_utils import BaseTestCase, parametrize_test_cases


class TestDataclassesEncoder(BaseTestCase):
    """Test cases for DataclassesEncoder."""

    def setUp(self):
        super().setUp()
        self.encoder = DataclassesEncoder()

    @parametrize_test_cases(
        [
            {"data": b"test bytes", "expected": "test bytes"},
            {"data": b"\x80\x81", "expected": "[Binary Data]"},
            {"data": b"", "expected": ""},
        ]
    )
    def test_encode_bytes(self, data: bytes, expected: str):
        """Test bytes encoding with various inputs."""
        result = self.encoder.default(data)
        assert result == expected

    def test_encode_pydantic_model(self):
        """Test Pydantic model encoding."""

        class TestModel(BaseModel):
            name: str = "test"
            value: int = 42

        model = TestModel(name="test", value=42)
        result = self.encoder.default(model)

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_encode_set(self):
        """Test set encoding."""
        test_set = {"a", "b", "c"}
        result = self.encoder.default(test_set)
        assert isinstance(result, list)
        assert len(result) == 3

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
            "model": TestModel(name="test", data=b"binary"),
            "bytes": b"test",
            "normal": "string",
        }

        result = json.dumps(test_data, cls=DataclassesEncoder)
        decoded = json.loads(result)

        assert decoded["model"]["name"] == "test"
        assert decoded["bytes"] == "test"
        assert decoded["normal"] == "string"


class TestFunctionNameUtils(BaseTestCase):
    """Test cases for function name utilities."""

    @parametrize_test_cases(
        [
            {"func_name": "get_function_name", "expected": True},
            {"func_name": "debug", "expected": True},
            {"func_name": "wrapper", "expected": True},
            {"func_name": "_record_raw_data_log", "expected": True},
            {"func_name": "trace", "expected": True},
        ]
    )
    def test_should_skip_function_skip_cases(self, func_name: str, expected: bool):
        """Test functions that should be skipped."""
        result = _should_skip_function(func_name)
        assert result == expected

    @parametrize_test_cases(
        [
            {"func_name": "__init__", "expected": False},
            {"func_name": "my_function", "expected": False},
            {"func_name": "process_data", "expected": False},
            {"func_name": "custom_method", "expected": False},
        ]
    )
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

    @patch('time.time')
    def test_agui_to_sse_conversion(self, mock_time):
        """Test converting AGUI event to SSE format."""
        mock_time.return_value = 1234567890.123
        
        # Create a mock BaseEvent
        mock_event = Mock(spec=BaseEvent)
        mock_event.type = Mock()
        mock_event.type.value = "test_event_type"
        mock_event.model_dump_json.return_value = '{"test": "data"}'
        
        result = agui_to_sse(mock_event)
        
        assert isinstance(result, dict)
        assert "data" in result
        assert "event" in result
        assert "id" in result
        assert result["event"] == "test_event_type"
        assert result["data"] == '{"test": "data"}'
        
        # Verify timestamp was set
        mock_event.__setattr__.assert_called_with("timestamp", 1234567890123)
        
        # Verify model_dump_json was called with correct parameters
        mock_event.model_dump_json.assert_called_once_with(
            by_alias=True, exclude_none=True, exclude={"type"}
        )

    def test_agui_to_sse_with_real_event_type(self):
        """Test conversion with real EventType enum."""
        mock_event = Mock(spec=BaseEvent)
        mock_event.type = EventType.TEXT_MESSAGE_START
        mock_event.model_dump_json.return_value = '{"message": "hello"}'
        
        result = agui_to_sse(mock_event)
        
        assert result["event"] == "text.message.start"
