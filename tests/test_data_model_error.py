"""Unit tests for adk_agui_middleware.data_model.error module."""

import time
import unittest
from unittest.mock import patch

from adk_agui_middleware.data_model.error import ErrorModel, ErrorResponseModel


class TestErrorModel(unittest.TestCase):
    """Test cases for the ErrorModel class."""

    def test_error_model_required_fields(self):
        """Test ErrorModel creation with required fields only."""
        error_model = ErrorModel(
            error="ValidationError",
            error_description="Invalid input data"
        )
        
        self.assertEqual(error_model.error, "ValidationError")
        self.assertEqual(error_model.error_description, "Invalid input data")
        self.assertIsInstance(error_model.timestamp, int)
        self.assertEqual(error_model.trace_id, "")

    def test_error_model_all_fields(self):
        """Test ErrorModel creation with all fields specified."""
        timestamp = int(time.time())
        error_model = ErrorModel(
            error="DatabaseError",
            error_description={"code": 500, "message": "Connection failed"},
            timestamp=timestamp,
            trace_id="abc123"
        )
        
        self.assertEqual(error_model.error, "DatabaseError")
        self.assertEqual(error_model.error_description, {"code": 500, "message": "Connection failed"})
        self.assertEqual(error_model.timestamp, timestamp)
        self.assertEqual(error_model.trace_id, "abc123")

    def test_error_model_description_dict(self):
        """Test ErrorModel with dictionary error description."""
        complex_description = {
            "field": "username",
            "constraint": "max_length",
            "limit": 50,
            "actual": 75
        }
        
        error_model = ErrorModel(
            error="ValidationError",
            error_description=complex_description
        )
        
        self.assertEqual(error_model.error_description, complex_description)

    def test_error_model_description_string(self):
        """Test ErrorModel with string error description."""
        error_model = ErrorModel(
            error="AuthError",
            error_description="Invalid credentials provided"
        )
        
        self.assertEqual(error_model.error_description, "Invalid credentials provided")

    def test_error_model_default_timestamp(self):
        """Test that ErrorModel generates current timestamp by default."""
        with patch('time.time', return_value=1234567890.5):
            error_model = ErrorModel(
                error="TestError",
                error_description="Test description"
            )
            
            self.assertEqual(error_model.timestamp, 1234567890)

    def test_error_model_timestamp_precision(self):
        """Test that timestamp is converted to integer."""
        # Use a float timestamp to verify conversion
        float_timestamp = 1234567890.789
        
        error_model = ErrorModel(
            error="TestError",
            error_description="Test description",
            timestamp=float_timestamp
        )
        
        self.assertEqual(error_model.timestamp, int(float_timestamp))
        self.assertIsInstance(error_model.timestamp, int)

    def test_error_model_empty_strings(self):
        """Test ErrorModel with empty strings for optional fields."""
        error_model = ErrorModel(
            error="",
            error_description="",
            trace_id=""
        )
        
        self.assertEqual(error_model.error, "")
        self.assertEqual(error_model.error_description, "")
        self.assertEqual(error_model.trace_id, "")

    def test_error_model_serialization(self):
        """Test ErrorModel can be serialized to dict."""
        error_model = ErrorModel(
            error="SerializationTest",
            error_description={"key": "value"},
            timestamp=1234567890,
            trace_id="trace123"
        )
        
        model_dict = error_model.model_dump()
        
        expected = {
            "error": "SerializationTest",
            "error_description": {"key": "value"},
            "timestamp": 1234567890,
            "trace_id": "trace123"
        }
        
        self.assertEqual(model_dict, expected)


class TestErrorResponseModel(unittest.TestCase):
    """Test cases for the ErrorResponseModel class."""

    def test_error_response_model_creation(self):
        """Test ErrorResponseModel creation with ErrorModel."""
        error_detail = ErrorModel(
            error="HTTPError",
            error_description="Bad request",
            timestamp=1234567890,
            trace_id="http123"
        )
        
        response_model = ErrorResponseModel(detail=error_detail)
        
        self.assertEqual(response_model.detail, error_detail)

    def test_error_response_model_nested_access(self):
        """Test accessing nested ErrorModel fields through ErrorResponseModel."""
        error_detail = ErrorModel(
            error="NestedTest",
            error_description="Nested access test"
        )
        
        response_model = ErrorResponseModel(detail=error_detail)
        
        self.assertEqual(response_model.detail.error, "NestedTest")
        self.assertEqual(response_model.detail.error_description, "Nested access test")

    def test_error_response_model_serialization(self):
        """Test ErrorResponseModel can be serialized to dict."""
        error_detail = ErrorModel(
            error="SerializationError",
            error_description="Response serialization test",
            timestamp=1234567890,
            trace_id="resp123"
        )
        
        response_model = ErrorResponseModel(detail=error_detail)
        model_dict = response_model.model_dump()
        
        expected = {
            "detail": {
                "error": "SerializationError",
                "error_description": "Response serialization test",
                "timestamp": 1234567890,
                "trace_id": "resp123"
            }
        }
        
        self.assertEqual(model_dict, expected)

    def test_error_response_model_from_dict(self):
        """Test ErrorResponseModel creation from dictionary."""
        error_data = {
            "detail": {
                "error": "FromDictError",
                "error_description": "Created from dict",
                "timestamp": 1234567890,
                "trace_id": "dict123"
            }
        }
        
        response_model = ErrorResponseModel(**error_data)
        
        self.assertEqual(response_model.detail.error, "FromDictError")
        self.assertEqual(response_model.detail.error_description, "Created from dict")
        self.assertEqual(response_model.detail.timestamp, 1234567890)
        self.assertEqual(response_model.detail.trace_id, "dict123")

    def test_error_response_model_validation(self):
        """Test ErrorResponseModel validation with invalid data."""
        from pydantic import ValidationError
        
        # Test missing required field
        with self.assertRaises(ValidationError):
            ErrorResponseModel()
        
        # Test invalid nested structure
        with self.assertRaises(ValidationError):
            ErrorResponseModel(detail="not_an_error_model")

    def test_complex_error_description_response(self):
        """Test ErrorResponseModel with complex error description."""
        complex_error = {
            "field_errors": [
                {"field": "email", "message": "Invalid format"},
                {"field": "password", "message": "Too short"}
            ],
            "global_error": "Authentication failed"
        }
        
        error_detail = ErrorModel(
            error="ValidationError",
            error_description=complex_error
        )
        
        response_model = ErrorResponseModel(detail=error_detail)
        
        self.assertEqual(response_model.detail.error_description, complex_error)

    def test_json_serialization_compatibility(self):
        """Test that the models work with JSON serialization."""
        import json
        
        error_detail = ErrorModel(
            error="JSONTest",
            error_description={"test": "json"},
            timestamp=1234567890,
            trace_id="json123"
        )
        
        response_model = ErrorResponseModel(detail=error_detail)
        
        # Test serialization through Pydantic
        json_str = response_model.model_dump_json()
        parsed_data = json.loads(json_str)
        
        self.assertEqual(parsed_data["detail"]["error"], "JSONTest")
        self.assertEqual(parsed_data["detail"]["error_description"]["test"], "json")


if __name__ == '__main__':
    unittest.main()