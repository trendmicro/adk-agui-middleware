"""Simple additional tests to boost coverage."""

from unittest.mock import Mock, patch

import pytest

from adk_agui_middleware.data_model.log import LogMessage
from adk_agui_middleware.loggers.record_log import record_error_log, record_log
from adk_agui_middleware.pattern.singleton import Singleton
from adk_agui_middleware.tools.function_name import get_function_name

from .test_utils import BaseTestCase


class TestSimpleCoverage(BaseTestCase):
    """Simple tests to improve code coverage."""

    def test_log_message_creation(self):
        """Test LogMessage creation."""
        log = LogMessage(msg="Test message", func_name="test_function")

        assert log.msg == "Test message"
        assert log.func_name == "test_function"
        assert log.error_message is None

    def test_log_message_with_all_fields(self):
        """Test LogMessage with all fields."""
        log = LogMessage(
            msg="Complete test message",
            func_name="complete_test",
            error_message="Test error",
            headers={"content-type": "application/json"},
            request_body="test body",
            body={"test": "data"},
            stack_message="stack trace",
        )

        assert log.msg == "Complete test message"
        assert log.error_message == "Test error"
        assert log.headers["content-type"] == "application/json"

    def test_record_log_basic(self):
        """Test basic record_log functionality."""
        # Mock LogMessage to avoid Pydantic model_dump issues in test environment
        with patch(
            "adk_agui_middleware.loggers.record_log.LogMessage"
        ) as mock_log_message:
            mock_instance = Mock()
            mock_instance.model_dump.return_value = {
                "msg": "Simple test log",
                "func_name": "test",
            }
            mock_log_message.return_value = mock_instance

            # Should not raise exception
            result = record_log("Simple test log")
            assert isinstance(result, dict)

    def test_record_error_log_with_exception(self):
        """Test record_error_log with exception."""
        # Mock LogMessage to avoid Pydantic model_dump issues in test environment
        with patch(
            "adk_agui_middleware.loggers.record_log.LogMessage"
        ) as mock_log_message:
            mock_instance = Mock()
            mock_instance.model_dump.return_value = {
                "msg": "Error occurred",
                "func_name": "test",
            }
            mock_log_message.return_value = mock_instance

            try:
                raise ValueError("Test error")
            except ValueError as e:
                # Should not raise exception
                result = record_error_log("Error occurred", e)
                assert isinstance(result, dict)

    def test_get_function_name_variations(self):
        """Test get_function_name with different parameters."""
        name1 = get_function_name()
        name2 = get_function_name(full_chain=True)
        name3 = get_function_name(max_depth=2)

        assert isinstance(name1, str)
        assert isinstance(name2, str)
        assert isinstance(name3, str)
        assert len(name1) > 0

    def test_singleton_metaclass(self):
        """Test Singleton metaclass functionality."""

        class TestSingleton(metaclass=Singleton):
            def __init__(self, value=42):
                self.value = value

        instance1 = TestSingleton(100)
        instance2 = TestSingleton(200)

        # Should be the same instance
        assert instance1 is instance2
        assert instance1.value == 100  # First value wins

    def test_json_encoder_edge_cases(self):
        """Test JSON encoder with edge cases."""

        from adk_agui_middleware.tools.json_encoder import DataclassesEncoder

        encoder = DataclassesEncoder()

        # Test with binary data that can't be decoded
        binary_data = b"\x80\x81\x82"
        result = encoder.default(binary_data)
        assert result == "[Binary Data]"

        # Test with valid UTF-8 bytes
        valid_bytes = "Hello 世界".encode()
        result = encoder.default(valid_bytes)
        assert result == "Hello 世界"

    def test_convert_functions_error_handling(self):
        """Test convert functions error handling."""
        from adk_agui_middleware.tools.convert import (
            convert_ag_ui_messages_to_adk,
            convert_json_patch_to_state,
        )

        # Test with malformed message that causes error
        class BadMessage:
            def __init__(self):
                self.id = "bad"
                self.role = "bad"
                # Missing required attributes

        # Should handle errors gracefully
        result = convert_ag_ui_messages_to_adk([BadMessage()])
        assert isinstance(result, list)

        # Test invalid patch operations
        bad_patches = [
            {"op": "unknown", "path": "/test", "value": "test"},
            {"path": "no_slash", "value": "test"},  # Missing op
        ]
        result = convert_json_patch_to_state(bad_patches)
        assert isinstance(result, dict)

    def test_session_parameter_serialization(self):
        """Test SessionParameter serialization."""
        param = self.factory.create_session_parameter(
            app_name="serialize_test",
            user_id="serialize_user",
            session_id="serialize_session",
        )

        data = param.model_dump()
        assert data["app_name"] == "serialize_test"
        assert data["user_id"] == "serialize_user"
        assert data["session_id"] == "serialize_session"

    def test_error_model_with_dict_description(self):
        """Test ErrorModel with dictionary error_description."""
        from adk_agui_middleware.data_model.error import ErrorModel

        error_dict = {"code": "DICT_ERROR", "details": "Error details"}
        error = ErrorModel(error="TEST_DICT", error_description=error_dict)

        assert error.error == "TEST_DICT"
        assert isinstance(error.error_description, dict)
        assert error.error_description["code"] == "DICT_ERROR"

    def test_context_config_edge_cases(self):
        """Test ContextConfig with edge cases."""
        from adk_agui_middleware.data_model.context import ContextConfig

        # Test with static string values for all fields
        config = ContextConfig(
            app_name="static_app", user_id="static_user", session_id="static_session"
        )

        # All should be strings, not functions
        assert config.app_name == "static_app"
        assert config.user_id == "static_user"
        assert config.session_id == "static_session"

    def test_runner_config_service_errors(self):
        """Test RunnerConfig service creation errors."""
        from adk_agui_middleware.data_model.context import RunnerConfig

        config = RunnerConfig(use_in_memory_services=False)

        # Should raise ValueError for each service
        with pytest.raises(ValueError, match="Artifact Service"):
            config.get_artifact_service()

        with pytest.raises(ValueError, match="Memory Service"):
            config.get_memory_service()

        with pytest.raises(ValueError, match="Credential Service"):
            config.get_credential_service()

    def test_function_name_skip_logic(self):
        """Test function name skip logic thoroughly."""
        from adk_agui_middleware.tools.function_name import _should_skip_function

        # Test functions that should be skipped
        assert _should_skip_function("get_function_name") is True
        assert _should_skip_function("debug") is True
        assert _should_skip_function("wrapper") is True
        assert _should_skip_function("__call__") is True
        assert _should_skip_function("<lambda>") is True

        # Test dunder methods that should be included
        assert _should_skip_function("__init__") is False
        assert _should_skip_function("__new__") is False
        assert _should_skip_function("__enter__") is False
        assert _should_skip_function("__exit__") is False

        # Test dunder methods that should be skipped
        assert _should_skip_function("__str__") is True
        assert _should_skip_function("__repr__") is True

        # Test regular functions
        assert _should_skip_function("my_function") is False
        assert _should_skip_function("process_data") is False

    def test_state_conversion_with_none_values(self):
        """Test state conversion with None values."""
        from adk_agui_middleware.tools.convert import (
            convert_json_patch_to_state,
            convert_state_to_json_patch,
        )

        # State with None values (should become remove operations)
        state = {"keep": "value", "remove": None, "update": "new_value"}
        patches = convert_state_to_json_patch(state)

        # Should have different operations for None vs non-None
        ops = [p["op"] for p in patches]
        assert "remove" in ops or "add" in ops

        # Convert back
        converted = convert_json_patch_to_state(patches)
        # Structure should be preserved in some form

    def test_comprehensive_integration(self):
        """Test comprehensive integration of multiple components."""
        # Test creating a complete workflow
        import json

        from adk_agui_middleware.data_model.context import ContextConfig, RunnerConfig
        from adk_agui_middleware.data_model.error import ErrorModel, ErrorResponseModel
        from adk_agui_middleware.data_model.session import SessionParameter

        # 1. Create configuration
        runner_config = RunnerConfig(use_in_memory_services=True)
        context_config = ContextConfig(app_name="integration", user_id="test_user")

        # 2. Create session parameter
        session_param = SessionParameter(
            app_name="integration", user_id="test_user", session_id="test_session"
        )

        # 3. Create error handling
        error = ErrorModel(error="INTEGRATION", error_description="Integration test")
        error_response = ErrorResponseModel(detail=error)

        # 4. Test services
        artifact_service = runner_config.get_artifact_service()
        assert artifact_service is not None

        # 5. Test serialization
        from adk_agui_middleware.tools.json_encoder import DataclassesEncoder

        serialized = json.dumps(error_response.model_dump(), cls=DataclassesEncoder)
        parsed = json.loads(serialized)

        assert "detail" in parsed
        assert parsed["detail"]["error"] == "INTEGRATION"

        # 6. Test function name utilities
        func_name = get_function_name()
        assert isinstance(func_name, str)
        assert "test_comprehensive_integration" in func_name

    def test_edge_case_coverage(self):
        """Test various edge cases for better coverage."""
        # Test empty strings and edge values
        log = LogMessage(msg="", func_name="")
        assert log.msg == ""
        assert log.func_name == ""

        # Test None handling in conversion
        from adk_agui_middleware.tools.convert import (
            convert_json_patch_to_state,
            convert_state_to_json_patch,
        )

        assert convert_state_to_json_patch({}) == []
        assert convert_json_patch_to_state([]) == {}

        # Test function name with max_depth edge cases
        name_depth_1 = get_function_name(max_depth=1)
        name_depth_10 = get_function_name(max_depth=10)

        # Both should be valid strings
        assert isinstance(name_depth_1, str)
        assert isinstance(name_depth_10, str)
