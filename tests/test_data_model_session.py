# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.data_model.session module."""

import os
import sys
import unittest


# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock pydantic before any imports
from unittest.mock import Mock


# Create a comprehensive mock for pydantic
class MockBaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def model_dump_json(self):
        import json

        return json.dumps(self.model_dump())


sys.modules["pydantic"] = Mock()
sys.modules["pydantic"].BaseModel = MockBaseModel

# Now we need to import the module directly without going through __init__.py
# Let's import the specific module file
import importlib.util


# Load the session module directly
spec = importlib.util.spec_from_file_location(
    "session_module",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "adk_agui_middleware",
        "data_model",
        "session.py",
    ),
)
session_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session_module)

# Get the SessionParameter class
SessionParameter = session_module.SessionParameter


class TestSessionParameter(unittest.TestCase):
    """Test cases for the SessionParameter model."""

    def test_session_parameter_creation(self):
        """Test SessionParameter creation with all required fields."""
        session_param = SessionParameter(
            app_name="test_app", user_id="user123", session_id="session456"
        )

        self.assertEqual(session_param.app_name, "test_app")
        self.assertEqual(session_param.user_id, "user123")
        self.assertEqual(session_param.session_id, "session456")

    def test_session_parameter_field_types(self):
        """Test that all fields are strings and properly validated."""
        session_param = SessionParameter(
            app_name="my_application",
            user_id="user@example.com",
            session_id="sess_abc123",
        )

        self.assertIsInstance(session_param.app_name, str)
        self.assertIsInstance(session_param.user_id, str)
        self.assertIsInstance(session_param.session_id, str)

    def test_session_parameter_empty_strings(self):
        """Test SessionParameter creation with empty strings (should be valid)."""
        session_param = SessionParameter(app_name="", user_id="", session_id="")

        self.assertEqual(session_param.app_name, "")
        self.assertEqual(session_param.user_id, "")
        self.assertEqual(session_param.session_id, "")

    def test_session_parameter_special_characters(self):
        """Test SessionParameter with special characters and various string formats."""
        session_param = SessionParameter(
            app_name="my-app_2023",
            user_id="user@domain.com",
            session_id="sess_123-456_abc",
        )

        self.assertEqual(session_param.app_name, "my-app_2023")
        self.assertEqual(session_param.user_id, "user@domain.com")
        self.assertEqual(session_param.session_id, "sess_123-456_abc")

    def test_session_parameter_unicode_strings(self):
        """Test SessionParameter with Unicode characters."""
        session_param = SessionParameter(
            app_name="应用程序", user_id="用户123", session_id="会话456"
        )

        self.assertEqual(session_param.app_name, "应用程序")
        self.assertEqual(session_param.user_id, "用户123")
        self.assertEqual(session_param.session_id, "会话456")

    def test_session_parameter_long_strings(self):
        """Test SessionParameter with very long strings."""
        long_app_name = "a" * 1000
        long_user_id = "u" * 500
        long_session_id = "s" * 750

        session_param = SessionParameter(
            app_name=long_app_name, user_id=long_user_id, session_id=long_session_id
        )

        self.assertEqual(session_param.app_name, long_app_name)
        self.assertEqual(session_param.user_id, long_user_id)
        self.assertEqual(session_param.session_id, long_session_id)

    def test_session_parameter_serialization(self):
        """Test SessionParameter can be serialized to dict."""
        session_param = SessionParameter(
            app_name="serialization_test",
            user_id="user_serialize",
            session_id="session_serialize",
        )

        serialized = session_param.model_dump()

        expected = {
            "app_name": "serialization_test",
            "user_id": "user_serialize",
            "session_id": "session_serialize",
        }

        self.assertEqual(serialized, expected)

    def test_session_parameter_json_serialization(self):
        """Test SessionParameter JSON serialization and deserialization."""
        import json

        original = SessionParameter(
            app_name="json_test", user_id="json_user", session_id="json_session"
        )

        # Serialize to JSON
        json_str = original.model_dump_json()
        json_data = json.loads(json_str)

        # Verify JSON content
        expected = {
            "app_name": "json_test",
            "user_id": "json_user",
            "session_id": "json_session",
        }

        self.assertEqual(json_data, expected)

    def test_session_parameter_equality(self):
        """Test SessionParameter field-by-field comparison."""
        param1 = SessionParameter(app_name="test", user_id="user", session_id="session")

        param2 = SessionParameter(app_name="test", user_id="user", session_id="session")

        param3 = SessionParameter(
            app_name="different", user_id="user", session_id="session"
        )

        # Test field by field equality
        self.assertEqual(param1.app_name, param2.app_name)
        self.assertEqual(param1.user_id, param2.user_id)
        self.assertEqual(param1.session_id, param2.session_id)

        # Test difference
        self.assertNotEqual(param1.app_name, param3.app_name)

    def test_session_parameter_mutability(self):
        """Test that SessionParameter fields can be modified after creation."""
        session_param = SessionParameter(
            app_name="original", user_id="original_user", session_id="original_session"
        )

        # Modify attributes
        session_param.app_name = "modified"
        self.assertEqual(session_param.app_name, "modified")

    def test_session_parameter_attribute_access(self):
        """Test that all attributes are accessible."""
        session_param = SessionParameter(
            app_name="access_test", user_id="user_access", session_id="session_access"
        )

        # Test attribute existence
        self.assertTrue(hasattr(session_param, "app_name"))
        self.assertTrue(hasattr(session_param, "user_id"))
        self.assertTrue(hasattr(session_param, "session_id"))

        # Test values via getattr
        self.assertEqual(session_param.app_name, "access_test")
        self.assertEqual(session_param.user_id, "user_access")
        self.assertEqual(session_param.session_id, "session_access")

    def test_session_parameter_string_representation(self):
        """Test string representation of SessionParameter."""
        session_param = SessionParameter(
            app_name="repr_test", user_id="repr_user", session_id="repr_session"
        )

        # Just verify it doesn't raise an error
        str_repr = str(session_param)
        self.assertIsInstance(str_repr, str)

    def test_session_parameter_model_fields(self):
        """Test that all expected fields are present in the model."""
        session_param = SessionParameter(
            app_name="field_test", user_id="field_user", session_id="field_session"
        )

        # Check that model_dump contains all expected fields
        model_dict = session_param.model_dump()

        expected_fields = {"app_name", "user_id", "session_id"}
        actual_fields = set(model_dict.keys())

        self.assertEqual(expected_fields, actual_fields)

    def test_session_parameter_type_preservation(self):
        """Test that field types are preserved correctly."""
        session_param = SessionParameter(
            app_name="type_test", user_id="type_user", session_id="type_session"
        )

        # All fields should be strings
        self.assertIsInstance(session_param.app_name, str)
        self.assertIsInstance(session_param.user_id, str)
        self.assertIsInstance(session_param.session_id, str)

        # Verify content is preserved
        self.assertEqual(session_param.app_name, "type_test")
        self.assertEqual(session_param.user_id, "type_user")
        self.assertEqual(session_param.session_id, "type_session")


if __name__ == "__main__":
    unittest.main()
