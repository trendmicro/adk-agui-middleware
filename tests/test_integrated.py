"""Simplified integrated test suite covering core functionality."""

import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

import pytest
from ag_ui.core import BaseEvent, EventType, RunAgentInput, UserMessage
from fastapi import FastAPI, Request
from google.adk.agents.run_config import StreamingMode

from adk_agui_middleware.data_model.context import (
    ConfigContext,
    RunnerConfig,
    default_session_id,
)
from adk_agui_middleware.data_model.error import ErrorModel, ErrorResponseModel
from adk_agui_middleware.data_model.session import SessionParameter
from adk_agui_middleware.endpoint import register_agui_endpoint
from adk_agui_middleware.tools.convert import agui_to_sse
from adk_agui_middleware.tools.function_name import (
    _should_skip_function,
    get_function_name,
)

from .test_utils import BaseTestCase


class TestIntegratedFunctionality(BaseTestCase):
    """Integrated test cases covering core functionality."""

    def setUp(self):
        super().setUp()
        self.app_name = "test_app"
        self.user_id = "test_user"
        self.session_id = "test_session"

    def test_session_parameter_creation(self):
        """Test SessionParameter model creation and validation."""
        param = SessionParameter(
            app_name=self.app_name,
            user_id=self.user_id, 
            session_id=self.session_id
        )
        
        assert param.app_name == self.app_name
        assert param.user_id == self.user_id
        assert param.session_id == self.session_id

    def test_config_context_creation(self):
        """Test ConfigContext creation with callables."""
        async def get_user_id(content, request):
            return self.user_id
            
        config = ConfigContext(
            app_name=self.app_name,
            user_id=get_user_id
        )
        
        assert config.app_name == self.app_name
        assert callable(config.user_id)

    def test_runner_config_services(self):
        """Test RunnerConfig service creation."""
        config = RunnerConfig()
        
        # Test service creation
        memory_service = config.get_memory_service()
        artifact_service = config.get_artifact_service()
        credential_service = config.get_credential_service()
        
        assert memory_service is not None
        assert artifact_service is not None
        assert credential_service is not None

    def test_error_models(self):
        """Test error model creation."""
        error = ErrorModel(
            code="TEST_ERROR",
            message="Test error message",
            details={"key": "value"}
        )
        
        response = ErrorResponseModel(error=error)
        
        assert error.code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert response.error == error

    def test_function_utilities(self):
        """Test function utility methods."""
        # Test function name skipping
        assert _should_skip_function("debug") is True
        assert _should_skip_function("custom_method") is False
        
        # Test get_function_name returns string
        result = get_function_name()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_agui_to_sse_conversion(self):
        """Test AGUI to SSE conversion."""
        mock_event = Mock(spec=BaseEvent)
        mock_event.type = EventType.TEXT_MESSAGE_START
        mock_event.model_dump_json.return_value = '{"message": "test"}'
        
        result = agui_to_sse(mock_event)
        
        assert isinstance(result, dict)
        assert "data" in result
        assert "event" in result
        assert "id" in result
        assert result["event"] == "TEXT_MESSAGE_START"

    def test_default_session_id_function(self):
        """Test default session ID extraction."""
        mock_content = Mock()
        mock_content.thread_id = "thread_123"
        
        result = default_session_id(mock_content, None)
        assert result == "thread_123"

    def test_endpoint_registration(self):
        """Test endpoint registration functionality."""
        app = FastAPI()
        
        async def mock_user_id(content, request):
            return "test_user"
            
        config = ConfigContext(app_name="test", user_id=mock_user_id)
        runner_config = RunnerConfig()
        mock_agent = Mock()
        
        # This should not raise an exception
        register_agui_endpoint(
            app=app,
            agent=mock_agent,
            runner_config=runner_config,
            context_config=config,
            path="/test"
        )
        
        # Verify endpoint was added
        routes = [route.path for route in app.routes]
        assert "/test" in routes

    def test_data_serialization(self):
        """Test data model serialization."""
        param = SessionParameter(
            app_name="test",
            user_id="user123",
            session_id="session456"
        )
        
        # Test JSON serialization
        json_str = param.model_dump_json()
        parsed = json.loads(json_str)
        
        assert parsed["app_name"] == "test"
        assert parsed["user_id"] == "user123"
        assert parsed["session_id"] == "session456"

    def test_streaming_mode_configuration(self):
        """Test streaming mode configuration."""
        config = RunnerConfig()
        
        # Test default streaming mode
        run_config = config.run_config
        assert hasattr(run_config, 'streaming_mode')

    def test_in_memory_services_toggle(self):
        """Test in-memory services configuration."""
        # Test with in-memory enabled
        config_enabled = RunnerConfig(use_in_memory_services=True)
        memory_service = config_enabled.get_memory_service()
        assert memory_service is not None
        
        # Test with in-memory disabled (should still work with external services)
        config_disabled = RunnerConfig(use_in_memory_services=False)
        # This might return None or external service depending on implementation
        memory_service_disabled = config_disabled.get_memory_service()
        # Just verify it doesn't crash

    def test_complex_workflow_simulation(self):
        """Test a complex workflow simulation."""
        # Create all components
        session_param = SessionParameter(
            app_name="integration_test",
            user_id="test_user_123", 
            session_id="session_abc"
        )
        
        async def extract_user(content, request):
            return session_param.user_id
            
        config = ConfigContext(
            app_name=session_param.app_name,
            user_id=extract_user
        )
        
        runner_config = RunnerConfig()
        
        # Test that all components can be created successfully
        assert session_param.app_name == "integration_test"
        assert config.app_name == "integration_test"
        assert runner_config.use_in_memory_services is True  # default

if __name__ == "__main__":
    unittest.main()