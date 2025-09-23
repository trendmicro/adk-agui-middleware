# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.tools.json_encoder module."""

import importlib.util
import json
import os
import sys
import unittest


# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock external dependencies
from unittest.mock import Mock


# Mock pydantic
class MockBaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


sys.modules["pydantic"] = Mock()
sys.modules["pydantic"].BaseModel = MockBaseModel

# Load the json_encoder module directly
spec = importlib.util.spec_from_file_location(
    "json_encoder_module",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "adk_agui_middleware",
        "tools",
        "json_encoder.py",
    ),
)
json_encoder_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(json_encoder_module)

# Get the DataclassesEncoder class
PydanticJsonEncoder = json_encoder_module.PydanticJsonEncoder


class MockPydanticModel(MockBaseModel):
    """Mock Pydantic model for testing."""

    def __init__(self, name="test", age=25, active=True):
        super().__init__(name=name, age=age, active=active)


class TestPydanticJsonEncoder(unittest.TestCase):
    """Test cases for the PydanticJsonEncoder class."""

    def setUp(self):
        """Set up test fixtures."""
        self.encoder = PydanticJsonEncoder()

    def test_encode_pydantic_model(self):
        """Test encoding a Pydantic BaseModel instance."""
        model = MockPydanticModel(name="test", age=25)

        result = self.encoder.default(model)
        expected = {"name": "test", "age": 25, "active": True}

        self.assertEqual(result, expected)

    def test_encode_bytes_object(self):
        """Test encoding a bytes object."""
        data = b"hello world"

        result = self.encoder.default(data)

        self.assertEqual(result, "hello world")

    def test_encode_utf8_bytes(self):
        """Test encoding UTF-8 bytes."""
        utf8_data = "Hello, 世界".encode()

        result = self.encoder.default(utf8_data)

        self.assertEqual(result, "Hello, 世界")

    def test_encode_empty_bytes(self):
        """Test encoding empty bytes."""
        empty_bytes = b""

        result = self.encoder.default(empty_bytes)

        self.assertEqual(result, "")

    def test_unsupported_object_raises_typeerror(self):
        """Test that unsupported objects raise TypeError."""
        unsupported_object = object()

        with self.assertRaises(TypeError):
            self.encoder.default(unsupported_object)

    def test_full_json_encoding_with_pydantic(self):
        """Test complete JSON encoding with Pydantic models."""
        model = MockPydanticModel(name="John", age=30, active=False)
        data = {"user": model, "metadata": "info"}

        json_string = json.dumps(data, cls=PydanticJsonEncoder)
        parsed = json.loads(json_string)

        expected = {
            "user": {"name": "John", "age": 30, "active": False},
            "metadata": "info",
        }

        self.assertEqual(parsed, expected)

    def test_full_json_encoding_with_bytes(self):
        """Test complete JSON encoding with bytes objects."""
        data = {
            "text": b"encoded text",
            "binary": b"\x00\x01\x02",
            "normal": "regular string",
        }

        json_string = json.dumps(data, cls=PydanticJsonEncoder)
        parsed = json.loads(json_string)

        expected = {
            "text": "encoded text",
            "binary": "\x00\x01\x02",
            "normal": "regular string",
        }

        self.assertEqual(parsed, expected)

    def test_nested_pydantic_models(self):
        """Test encoding nested Pydantic models."""

        class AddressModel(MockBaseModel):
            def __init__(self, street="123 Main St", city="Anytown"):
                super().__init__(street=street, city=city)

        class PersonModel(MockBaseModel):
            def __init__(self, name="Alice", address=None):
                super().__init__(name=name, address=address)

        address = AddressModel(street="123 Main St", city="Anytown")
        person = PersonModel(name="Alice", address=address)

        # For testing nested models, we need to use JSON dumps with the encoder
        json_string = json.dumps(person, cls=PydanticJsonEncoder)
        result = json.loads(json_string)

        expected = {
            "name": "Alice",
            "address": {"street": "123 Main St", "city": "Anytown"},
        }

        self.assertEqual(result, expected)

    def test_complex_mixed_data(self):
        """Test encoding complex data with mixed types."""

        class DataModel(MockBaseModel):
            def __init__(self, id=1, metadata=None):
                super().__init__(id=id, metadata=metadata or {})

        complex_data = {
            "models": [
                DataModel(id=1, metadata={"key": "value1"}),
                DataModel(id=2, metadata={"key": "value2"}),
            ],
            "binary_data": b"binary content",
            "raw_dict": {"nested": {"deep": "value"}},
            "simple_list": [1, 2, 3],
        }

        json_string = json.dumps(complex_data, cls=PydanticJsonEncoder)
        parsed = json.loads(json_string)

        expected = {
            "models": [
                {"id": 1, "metadata": {"key": "value1"}},
                {"id": 2, "metadata": {"key": "value2"}},
            ],
            "binary_data": "binary content",
            "raw_dict": {"nested": {"deep": "value"}},
            "simple_list": [1, 2, 3],
        }

        self.assertEqual(parsed, expected)

    def test_encoder_inheritance(self):
        """Test that PydanticJsonEncoder properly inherits from JSONEncoder."""
        self.assertIsInstance(self.encoder, json.JSONEncoder)

    def test_pydantic_model_with_optional_fields(self):
        """Test encoding Pydantic model with optional fields."""

        class OptionalModel(MockBaseModel):
            def __init__(self, required="test", optional=None):
                super().__init__(required=required, optional=optional)

        # Test with optional field set
        model_with_optional = OptionalModel(required="test", optional="value")
        result = self.encoder.default(model_with_optional)
        self.assertEqual(result, {"required": "test", "optional": "value"})

        # Test with optional field not set
        model_without_optional = OptionalModel(required="test")
        result = self.encoder.default(model_without_optional)
        self.assertEqual(result, {"required": "test", "optional": None})

    def test_pydantic_model_with_default_values(self):
        """Test encoding Pydantic model with default values."""

        class DefaultModel(MockBaseModel):
            def __init__(self, name="test", count=0, enabled=True):
                super().__init__(name=name, count=count, enabled=enabled)

        model = DefaultModel(name="test")
        result = self.encoder.default(model)

        expected = {"name": "test", "count": 0, "enabled": True}
        self.assertEqual(result, expected)

    def test_bytes_decoding_error_handling(self):
        """Test handling of bytes that cannot be decoded as UTF-8."""
        # Create bytes with invalid UTF-8 sequence
        invalid_utf8 = b"\xff\xfe\xfd"

        # The default decoder behavior should handle this
        try:
            result = self.encoder.default(invalid_utf8)
            self.assertIsInstance(result, str)
        except UnicodeDecodeError:
            # This is also acceptable behavior
            pass

    def test_model_dump_called_on_basemodel(self):
        """Test that model_dump() is called on BaseModel instances."""
        model = MockPydanticModel(name="test", age=25)

        # Test that our mock works correctly
        result = self.encoder.default(model)
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertIn("age", result)

    def test_edge_case_empty_pydantic_model(self):
        """Test encoding an empty Pydantic model."""

        class EmptyModel(MockBaseModel):
            def __init__(self):
                super().__init__()

        empty_model = EmptyModel()
        result = self.encoder.default(empty_model)

        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
