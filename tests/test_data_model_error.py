# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.data_model.error module."""

import importlib.util
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

    def model_dump_json(self):
        import json

        return json.dumps(self.model_dump())


def mock_field(default=None, default_factory=None, **kwargs):
    """Mock pydantic Field function that handles default_factory."""
    if default_factory is not None:
        return default_factory()
    return default


sys.modules["pydantic"] = Mock()
sys.modules["pydantic"].BaseModel = MockBaseModel
sys.modules["pydantic"].Field = mock_field

# Load the error module directly
spec = importlib.util.spec_from_file_location(
    "error_module",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "adk_agui_middleware",
        "data_model",
        "error.py",
    ),
)
error_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(error_module)

ErrorModel = error_module.ErrorModel
ErrorResponseModel = error_module.ErrorResponseModel


class TestErrorModel(unittest.TestCase):
    """Test cases for the ErrorModel class."""

    def test_error_model_creation(self):
        """Test ErrorModel creation."""
        error_model = ErrorModel(
            error="TestError", error_description="Test description"
        )

        self.assertEqual(error_model.error, "TestError")
        self.assertEqual(error_model.error_description, "Test description")
        self.assertIsInstance(error_model.timestamp, int)
        self.assertEqual(error_model.trace_id, "")

    def test_error_model_serialization(self):
        """Test ErrorModel serialization."""
        error_model = ErrorModel(
            error="SerializationTest",
            error_description={"key": "value"},
            timestamp=1234567890,
            trace_id="trace123",
        )

        model_dict = error_model.model_dump()

        expected = {
            "error": "SerializationTest",
            "error_description": {"key": "value"},
            "timestamp": 1234567890,
            "trace_id": "trace123",
        }

        self.assertEqual(model_dict, expected)


class TestErrorResponseModel(unittest.TestCase):
    """Test cases for the ErrorResponseModel class."""

    def test_error_response_model_creation(self):
        """Test ErrorResponseModel creation."""
        error_detail = ErrorModel(error="HTTPError", error_description="Bad request")

        response_model = ErrorResponseModel(detail=error_detail)
        self.assertEqual(response_model.detail, error_detail)


if __name__ == "__main__":
    unittest.main()
