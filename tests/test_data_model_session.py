"""Unit tests for adk_agui_middleware.data_model.session module."""

import unittest

from pydantic import ValidationError

from adk_agui_middleware.data_model.session import SessionParameter


class TestSessionParameter(unittest.TestCase):
    """Test cases for the SessionParameter model."""

    def test_session_parameter_creation(self):
        """Test SessionParameter creation with all required fields."""
        session_param = SessionParameter(
            app_name="test_app",
            user_id="user123",
            session_id="session456"
        )
        
        self.assertEqual(session_param.app_name, "test_app")
        self.assertEqual(session_param.user_id, "user123")
        self.assertEqual(session_param.session_id, "session456")

    def test_session_parameter_field_types(self):
        """Test that all fields are strings and properly validated."""
        session_param = SessionParameter(
            app_name="my_application",
            user_id="user@example.com",
            session_id="sess_abc123"
        )
        
        self.assertIsInstance(session_param.app_name, str)
        self.assertIsInstance(session_param.user_id, str)
        self.assertIsInstance(session_param.session_id, str)

    def test_session_parameter_missing_app_name(self):
        """Test that SessionParameter raises ValidationError when app_name is missing."""
        with self.assertRaises(ValidationError) as cm:
            SessionParameter(
                user_id="user123",
                session_id="session456"
            )
        
        errors = cm.exception.errors()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['type'], 'missing')
        self.assertEqual(errors[0]['loc'], ('app_name',))

    def test_session_parameter_missing_user_id(self):
        """Test that SessionParameter raises ValidationError when user_id is missing."""
        with self.assertRaises(ValidationError) as cm:
            SessionParameter(
                app_name="test_app",
                session_id="session456"
            )
        
        errors = cm.exception.errors()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['type'], 'missing')
        self.assertEqual(errors[0]['loc'], ('user_id',))

    def test_session_parameter_missing_session_id(self):
        """Test that SessionParameter raises ValidationError when session_id is missing."""
        with self.assertRaises(ValidationError) as cm:
            SessionParameter(
                app_name="test_app",
                user_id="user123"
            )
        
        errors = cm.exception.errors()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['type'], 'missing')
        self.assertEqual(errors[0]['loc'], ('session_id',))

    def test_session_parameter_missing_all_fields(self):
        """Test that SessionParameter raises ValidationError when all fields are missing."""
        with self.assertRaises(ValidationError) as cm:
            SessionParameter()
        
        errors = cm.exception.errors()
        self.assertEqual(len(errors), 3)
        
        # Check that all required fields are mentioned in errors
        missing_fields = {error['loc'][0] for error in errors}
        expected_fields = {'app_name', 'user_id', 'session_id'}
        self.assertEqual(missing_fields, expected_fields)

    def test_session_parameter_empty_strings(self):
        """Test SessionParameter creation with empty strings (should be valid)."""
        session_param = SessionParameter(
            app_name="",
            user_id="",
            session_id=""
        )
        
        self.assertEqual(session_param.app_name, "")
        self.assertEqual(session_param.user_id, "")
        self.assertEqual(session_param.session_id, "")

    def test_session_parameter_special_characters(self):
        """Test SessionParameter with special characters and various string formats."""
        session_param = SessionParameter(
            app_name="my-app_2023",
            user_id="user@domain.com",
            session_id="sess_123-456_abc"
        )
        
        self.assertEqual(session_param.app_name, "my-app_2023")
        self.assertEqual(session_param.user_id, "user@domain.com")
        self.assertEqual(session_param.session_id, "sess_123-456_abc")

    def test_session_parameter_unicode_strings(self):
        """Test SessionParameter with Unicode characters."""
        session_param = SessionParameter(
            app_name="应用程序",
            user_id="用户123",
            session_id="会话456"
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
            app_name=long_app_name,
            user_id=long_user_id,
            session_id=long_session_id
        )
        
        self.assertEqual(session_param.app_name, long_app_name)
        self.assertEqual(session_param.user_id, long_user_id)
        self.assertEqual(session_param.session_id, long_session_id)

    def test_session_parameter_serialization(self):
        """Test SessionParameter can be serialized to dict."""
        session_param = SessionParameter(
            app_name="serialization_test",
            user_id="user_serialize",
            session_id="session_serialize"
        )
        
        serialized = session_param.model_dump()
        
        expected = {
            "app_name": "serialization_test",
            "user_id": "user_serialize",
            "session_id": "session_serialize"
        }
        
        self.assertEqual(serialized, expected)

    def test_session_parameter_from_dict(self):
        """Test SessionParameter creation from dictionary."""
        data = {
            "app_name": "dict_app",
            "user_id": "dict_user",
            "session_id": "dict_session"
        }
        
        session_param = SessionParameter(**data)
        
        self.assertEqual(session_param.app_name, "dict_app")
        self.assertEqual(session_param.user_id, "dict_user")
        self.assertEqual(session_param.session_id, "dict_session")

    def test_session_parameter_json_serialization(self):
        """Test SessionParameter JSON serialization and deserialization."""
        import json
        
        original = SessionParameter(
            app_name="json_test",
            user_id="json_user",
            session_id="json_session"
        )
        
        # Serialize to JSON
        json_str = original.model_dump_json()
        json_data = json.loads(json_str)
        
        # Deserialize from JSON
        recreated = SessionParameter(**json_data)
        
        self.assertEqual(original.app_name, recreated.app_name)
        self.assertEqual(original.user_id, recreated.user_id)
        self.assertEqual(original.session_id, recreated.session_id)

    def test_session_parameter_equality(self):
        """Test SessionParameter equality comparison."""
        param1 = SessionParameter(
            app_name="test",
            user_id="user",
            session_id="session"
        )
        
        param2 = SessionParameter(
            app_name="test",
            user_id="user",
            session_id="session"
        )
        
        param3 = SessionParameter(
            app_name="different",
            user_id="user",
            session_id="session"
        )
        
        self.assertEqual(param1, param2)
        self.assertNotEqual(param1, param3)

    def test_session_parameter_immutability(self):
        """Test that SessionParameter fields can be modified after creation."""
        session_param = SessionParameter(
            app_name="original",
            user_id="original_user",
            session_id="original_session"
        )
        
        # Pydantic models are mutable by default
        session_param.app_name = "modified"
        self.assertEqual(session_param.app_name, "modified")


if __name__ == '__main__':
    unittest.main()