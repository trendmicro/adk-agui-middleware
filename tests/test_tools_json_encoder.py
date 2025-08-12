"""Unit tests for adk_agui_middleware.tools.json_encoder module."""

import json
import unittest

from pydantic import BaseModel

from adk_agui_middleware.tools.json_encoder import DataclassesEncoder


class MockPydanticModel(BaseModel):
    """Mock Pydantic model for testing."""
    name: str
    age: int
    active: bool = True


class TestDataclassesEncoder(unittest.TestCase):
    """Test cases for the DataclassesEncoder class."""

    def setUp(self):
        """Set up test fixtures."""
        self.encoder = DataclassesEncoder()

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
        utf8_data = "Hello, 世界".encode('utf-8')
        
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
        
        json_string = json.dumps(data, cls=DataclassesEncoder)
        parsed = json.loads(json_string)
        
        expected = {
            "user": {"name": "John", "age": 30, "active": False},
            "metadata": "info"
        }
        
        self.assertEqual(parsed, expected)

    def test_full_json_encoding_with_bytes(self):
        """Test complete JSON encoding with bytes objects."""
        data = {
            "text": b"encoded text",
            "binary": b"\x00\x01\x02",
            "normal": "regular string"
        }
        
        json_string = json.dumps(data, cls=DataclassesEncoder)
        parsed = json.loads(json_string)
        
        expected = {
            "text": "encoded text",
            "binary": "\x00\x01\x02",
            "normal": "regular string"
        }
        
        self.assertEqual(parsed, expected)

    def test_nested_pydantic_models(self):
        """Test encoding nested Pydantic models."""
        class AddressModel(BaseModel):
            street: str
            city: str
        
        class PersonModel(BaseModel):
            name: str
            address: AddressModel
        
        address = AddressModel(street="123 Main St", city="Anytown")
        person = PersonModel(name="Alice", address=address)
        
        result = self.encoder.default(person)
        
        expected = {
            "name": "Alice",
            "address": {"street": "123 Main St", "city": "Anytown"}
        }
        
        self.assertEqual(result, expected)

    def test_complex_mixed_data(self):
        """Test encoding complex data with mixed types."""
        class DataModel(BaseModel):
            id: int
            metadata: dict
        
        complex_data = {
            "models": [
                DataModel(id=1, metadata={"key": "value1"}),
                DataModel(id=2, metadata={"key": "value2"})
            ],
            "binary_data": b"binary content",
            "raw_dict": {"nested": {"deep": "value"}},
            "simple_list": [1, 2, 3]
        }
        
        json_string = json.dumps(complex_data, cls=DataclassesEncoder)
        parsed = json.loads(json_string)
        
        expected = {
            "models": [
                {"id": 1, "metadata": {"key": "value1"}},
                {"id": 2, "metadata": {"key": "value2"}}
            ],
            "binary_data": "binary content",
            "raw_dict": {"nested": {"deep": "value"}},
            "simple_list": [1, 2, 3]
        }
        
        self.assertEqual(parsed, expected)

    def test_encoder_inheritance(self):
        """Test that DataclassesEncoder properly inherits from JSONEncoder."""
        self.assertIsInstance(self.encoder, json.JSONEncoder)

    def test_pydantic_model_with_optional_fields(self):
        """Test encoding Pydantic model with optional fields."""
        class OptionalModel(BaseModel):
            required: str
            optional: str | None = None
        
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
        class DefaultModel(BaseModel):
            name: str
            count: int = 0
            enabled: bool = True
        
        model = DefaultModel(name="test")
        result = self.encoder.default(model)
        
        expected = {"name": "test", "count": 0, "enabled": True}
        self.assertEqual(result, expected)

    def test_bytes_decoding_error_handling(self):
        """Test handling of bytes that cannot be decoded as UTF-8."""
        # Create bytes with invalid UTF-8 sequence
        invalid_utf8 = b'\xff\xfe\xfd'
        
        # The default decoder behavior should handle this
        # The exact behavior depends on the decode() method's error handling
        try:
            result = self.encoder.default(invalid_utf8)
            self.assertIsInstance(result, str)
        except UnicodeDecodeError:
            # This is also acceptable behavior
            pass

    def test_model_dump_called_on_basemodel(self):
        """Test that model_dump() is called on BaseModel instances."""
        model = MockPydanticModel(name="test", age=25)
        
        # Mock the model_dump method to verify it's called
        original_model_dump = model.model_dump
        call_count = 0
        
        def mock_model_dump():
            nonlocal call_count
            call_count += 1
            return original_model_dump()
        
        model.model_dump = mock_model_dump
        
        self.encoder.default(model)
        
        self.assertEqual(call_count, 1)

    def test_edge_case_empty_pydantic_model(self):
        """Test encoding an empty Pydantic model."""
        class EmptyModel(BaseModel):
            pass
        
        empty_model = EmptyModel()
        result = self.encoder.default(empty_model)
        
        self.assertEqual(result, {})


if __name__ == '__main__':
    unittest.main()