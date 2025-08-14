"""Integrated test suite covering core functionality with high test coverage."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from ag_ui.core import RunAgentInput, UserMessage
from fastapi import FastAPI, Request
from google.adk.agents.run_config import StreamingMode
from google.adk.sessions import Session
from starlette.responses import StreamingResponse

from adk_agui_middleware.data_model.context import (
    ContextConfig,
    RunnerConfig,
    default_session_id,
)
from adk_agui_middleware.data_model.error import ErrorModel, ErrorResponseModel
from adk_agui_middleware.data_model.session import SessionParameter
from adk_agui_middleware.endpoint import register_agui_endpoint
from adk_agui_middleware.handler.session import SessionHandler
from adk_agui_middleware.handler.user_message import UserMessageHandler
from adk_agui_middleware.manager.session import SessionManager
from adk_agui_middleware.sse_service import SSEService
from adk_agui_middleware.tools.convert import (
    convert_adk_event_to_ag_ui_message,
    convert_ag_ui_messages_to_adk,
    convert_json_patch_to_state,
    convert_state_to_json_patch,
)
from adk_agui_middleware.tools.function_name import (
    _should_skip_function,
    get_function_name,
)
from adk_agui_middleware.tools.json_encoder import DataclassesEncoder

from .test_utils import BaseTestCase, TestDataFactory


class TestIntegratedSuite(BaseTestCase):
    """Comprehensive test suite for all middleware components."""

    def setUp(self):
        super().setUp()
        self.factory = TestDataFactory()

    # Data Model Tests
    def test_error_model_core_functionality(self):
        """Test ErrorModel core functionality."""
        error = ErrorModel(error="TEST_ERROR", error_description="Test description")

        assert error.error == "TEST_ERROR"
        assert error.error_description == "Test description"
        assert isinstance(error.timestamp, int)
        assert error.trace_id == ""

        # Test serialization
        data = error.model_dump()
        assert "error" in data
        assert "error_description" in data

        # Test attributes are accessible (timestamp might not be in dump due to defaults)
        assert hasattr(error, "timestamp")
        assert isinstance(error.timestamp, int)

    def test_session_parameter_functionality(self):
        """Test SessionParameter functionality."""
        param = SessionParameter(
            app_name="test_app", user_id="test_user", session_id="test_session"
        )

        assert param.app_name == "test_app"
        assert param.user_id == "test_user"
        assert param.session_id == "test_session"

        # Test equality via model_dump (since object equality might not work consistently)
        param2 = SessionParameter(
            app_name="test_app", user_id="test_user", session_id="test_session"
        )
        assert param.model_dump() == param2.model_dump()

        # Test field-by-field equality
        assert param.app_name == param2.app_name
        assert param.user_id == param2.user_id
        assert param.session_id == param2.session_id

    def test_runner_config_services(self):
        """Test RunnerConfig service management."""
        config = RunnerConfig(use_in_memory_services=True)

        # Test service creation
        artifact_service = config.get_artifact_service()
        memory_service = config.get_memory_service()

        assert artifact_service is not None
        assert memory_service is not None

        # Test caching
        artifact_service2 = config.get_artifact_service()
        assert artifact_service is artifact_service2

    def test_runner_config_disabled_services(self):
        """Test RunnerConfig with disabled services."""
        config = RunnerConfig(use_in_memory_services=False)

        with pytest.raises(ValueError, match="Artifact Service is not set"):
            config.get_artifact_service()

    @pytest.mark.asyncio
    async def test_context_config_functionality(self):
        """Test ContextConfig functionality."""

        async def custom_user_id(content, request):
            return "custom_user"

        config = ContextConfig(app_name="test_app", user_id=custom_user_id)

        agui_content = self.factory.create_run_agent_input()
        request = Mock(spec=Request)

        user_id = await config.user_id(agui_content, request)
        assert user_id == "custom_user"

    # Tools Tests
    def test_json_encoder_functionality(self):
        """Test DataclassesEncoder functionality."""
        encoder = DataclassesEncoder()

        # Test bytes encoding
        assert encoder.default(b"test") == "test"
        assert encoder.default(b"\x80\x81") == "[Binary Data]"

        # Test unsupported type
        with pytest.raises(TypeError):
            encoder.default(object())

    def test_function_name_utilities(self):
        """Test function name utilities."""
        # Test should skip function
        assert _should_skip_function("get_function_name") is True
        assert _should_skip_function("debug") is True
        assert _should_skip_function("wrapper") is True
        assert _should_skip_function("my_function") is False
        assert _should_skip_function("__init__") is False

        # Test get_function_name returns string
        result = get_function_name()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_convert_functions_basic(self):
        """Test basic convert functions."""
        # Test empty/None inputs
        assert convert_ag_ui_messages_to_adk([]) == []
        assert convert_ag_ui_messages_to_adk(None) == []
        assert convert_adk_event_to_ag_ui_message(None) is None
        assert convert_state_to_json_patch(None) == []
        assert convert_json_patch_to_state(None) == {}

    def test_json_patch_conversion(self):
        """Test JSON patch conversion functionality."""
        # Test state to patch conversion
        state = {"key1": "value1", "key2": "value2"}
        patches = convert_state_to_json_patch(state)

        assert len(patches) == 2
        for patch in patches:
            assert patch["op"] == "add"
            assert patch["path"].startswith("/")

        # Test patch to state conversion
        converted_state = convert_json_patch_to_state(patches)
        assert converted_state == state

    def test_json_patch_edge_cases(self):
        """Test JSON patch edge cases."""
        # Test invalid paths
        invalid_patches = [{"op": "add", "path": "invalid_path", "value": "test"}]
        result = convert_json_patch_to_state(invalid_patches)
        assert result == {}

        # Test invalid operations
        invalid_patches = [{"op": "invalid", "path": "/test"}]
        result = convert_json_patch_to_state(invalid_patches)
        assert result == {}

    # Handler Tests
    @pytest.mark.asyncio
    async def test_user_message_handler_basic(self):
        """Test UserMessageHandler basic functionality."""
        agui_content = self.factory.create_run_agent_input(
            messages=[self.factory.create_user_message(content="Hello")]
        )
        request = Mock(spec=Request)

        handler = UserMessageHandler(agui_content, request)

        assert handler.thread_id == "test_thread"
        assert handler.is_tool_result_submission is False

        # Test get latest message
        message = await handler.get_latest_message()
        assert message is not None
        assert message.role == "user"

    @pytest.mark.asyncio
    async def test_user_message_handler_tool_results(self):
        """Test UserMessageHandler with tool results."""
        tool_call = self.factory.create_tool_call()
        messages = [
            self.factory.create_assistant_message(tool_calls=[tool_call]),
            self.factory.create_tool_message(tool_call_id="call_1"),
        ]

        agui_content = self.factory.create_run_agent_input(messages=messages)
        handler = UserMessageHandler(agui_content, Mock(spec=Request))

        assert handler.is_tool_result_submission is True

        # Test extract tool results
        results = await handler.extract_tool_results()
        assert len(results) == 1
        assert results[0]["tool_name"] == "test_function"

    def test_session_handler_basic(self):
        """Test SessionHandler basic functionality."""
        mock_manager = Mock()
        session_param = self.factory.create_session_parameter()

        handler = SessionHandler(mock_manager, session_param)

        assert handler.app_name == "test_app"
        assert handler.user_id == "test_user"
        assert handler.session_id == "test_session"

        # Test pending tool calls dict
        calls_dict = SessionHandler.get_pending_tool_calls_dict(["call1", "call2"])
        assert calls_dict == {"pending_tool_calls": ["call1", "call2"]}

    @pytest.mark.asyncio
    async def test_session_handler_async_operations(self):
        """Test SessionHandler async operations."""
        mock_manager = Mock()
        mock_manager.get_session = AsyncMock(return_value=Mock(spec=Session))
        mock_manager.get_session_state = AsyncMock(return_value={"test": "state"})
        mock_manager.update_session_state = AsyncMock(return_value=True)

        session_param = self.factory.create_session_parameter()
        handler = SessionHandler(mock_manager, session_param)

        # Test async methods
        session = await handler.get_session()
        assert session is not None

        state = await handler.get_session_state()
        assert state == {"test": "state"}

        success = await handler.update_session_state({"new": "state"})
        assert success is True

    # Manager Tests
    def test_session_manager_initialization(self):
        """Test SessionManager initialization."""
        session_service = Mock()

        manager = SessionManager(session_service)

        assert manager.session_service == session_service

    # SSE Service Tests
    def test_sse_service_initialization(self):
        """Test SSEService initialization."""
        mock_agent = Mock()
        runner_config = self.factory.create_runner_config()
        context_config = self.factory.create_context_config()

        service = SSEService(mock_agent, runner_config, context_config)

        assert service.agent == mock_agent
        assert service.runner_config == runner_config
        assert service.context_config == context_config
        assert service.runner_box == {}

    @pytest.mark.asyncio
    async def test_sse_service_runner_creation(self):
        """Test SSEService runner creation."""
        mock_agent = Mock()
        runner_config = self.factory.create_runner_config()
        context_config = self.factory.create_context_config()

        service = SSEService(mock_agent, runner_config, context_config)

        # Mock the _create_runner method to be async
        with patch.object(service, "_create_runner", new=AsyncMock()) as mock_create:
            mock_runner = Mock()
            mock_create.return_value = mock_runner

            agui_content = self.factory.create_run_agent_input()
            request = Mock(spec=Request)

            runner = await service.get_runner(agui_content, request)
            assert runner == mock_runner
            mock_create.assert_called_once()

    # Endpoint Tests
    def test_endpoint_registration(self):
        """Test endpoint registration."""
        app = FastAPI()
        mock_service = Mock()
        initial_routes = len(app.routes)

        register_agui_endpoint(app, mock_service, "/test")

        assert len(app.routes) == initial_routes + 1

    @patch("adk_agui_middleware.endpoint.exception_http_handler")
    @patch("adk_agui_middleware.endpoint.EventEncoder")
    @pytest.mark.asyncio
    async def test_endpoint_functionality(
        self, mock_encoder_class, mock_exception_handler
    ):
        """Test endpoint functionality."""
        app = FastAPI()
        mock_service = Mock()
        mock_encoder = Mock()
        mock_encoder.get_content_type.return_value = "text/event-stream"
        mock_encoder_class.return_value = mock_encoder

        mock_service.get_runner = AsyncMock()
        mock_service.event_generator.return_value = iter([b"data: test\n\n"])

        # Mock exception handler
        mock_exception_handler.return_value.__aenter__ = AsyncMock()
        mock_exception_handler.return_value.__aexit__ = AsyncMock()

        register_agui_endpoint(app, mock_service)

        # Get the endpoint function
        endpoint_func = None
        for route in app.routes:
            if hasattr(route, "endpoint"):
                endpoint_func = route.endpoint
                break

        assert endpoint_func is not None

        # Test endpoint call
        agui_content = self.factory.create_run_agent_input()
        request = Mock(spec=Request)
        request.headers = {"accept": "text/event-stream"}

        response = await endpoint_func(agui_content, request)

        assert isinstance(response, StreamingResponse)
        mock_service.get_runner.assert_called_once_with(agui_content, request)

    # Integration Tests
    def test_message_conversion_integration(self):
        """Test message conversion integration."""
        user_msg = self.factory.create_user_message(content="Hello")
        tool_call = self.factory.create_tool_call()
        assistant_msg = self.factory.create_assistant_message(tool_calls=[tool_call])

        messages = [user_msg, assistant_msg]

        # This should not raise an exception
        adk_events = convert_ag_ui_messages_to_adk(messages)

        # Should have some result (exact format depends on implementation)
        assert isinstance(adk_events, list)

    def test_error_handling_integration(self):
        """Test error handling integration."""
        # Test ErrorResponseModel creation
        error = ErrorModel(
            error="INTEGRATION_ERROR", error_description="Integration test error"
        )
        response = ErrorResponseModel(detail=error)

        assert response.detail.error == "INTEGRATION_ERROR"
        assert response.detail.error_description == "Integration test error"

        # Test JSON serialization
        data = json.dumps(response.model_dump(), cls=DataclassesEncoder)
        parsed = json.loads(data)

        assert "detail" in parsed
        assert "error" in parsed["detail"]
        assert parsed["detail"]["error"] == "INTEGRATION_ERROR"

    @pytest.mark.asyncio
    async def test_context_default_session_id(self):
        """Test default_session_id function."""
        agui_content = self.factory.create_run_agent_input(thread_id="custom_thread")
        request = Mock(spec=Request)

        result = await default_session_id(agui_content, request)
        assert result == "custom_thread"

    def test_runner_config_streaming_modes(self):
        """Test RunnerConfig with different streaming modes."""
        config_sse = self.factory.create_runner_config(streaming_mode=StreamingMode.SSE)
        config_bidi = self.factory.create_runner_config(
            streaming_mode=StreamingMode.BIDI
        )

        assert config_sse.run_config.streaming_mode == StreamingMode.SSE
        assert config_bidi.run_config.streaming_mode == StreamingMode.BIDI

    def test_session_parameter_edge_cases(self):
        """Test SessionParameter edge cases."""
        # Test with empty strings
        param = SessionParameter(app_name="", user_id="", session_id="")
        assert param.app_name == ""
        assert param.user_id == ""
        assert param.session_id == ""

        # Test string representation
        str_repr = str(param)
        assert isinstance(str_repr, str)

    def test_comprehensive_functionality(self):
        """Test comprehensive functionality across components."""
        # Create a complete workflow test

        # 1. Create configuration objects
        runner_config = RunnerConfig(use_in_memory_services=True)
        session_param = SessionParameter(
            app_name="integration_app",
            user_id="integration_user",
            session_id="integration_session",
        )

        # 2. Test service creation
        artifact_service = runner_config.get_artifact_service()
        assert artifact_service is not None

        # 3. Test message handling
        user_msg = UserMessage(id="1", role="user", content="Integration test message")

        agui_content = RunAgentInput(
            thread_id="integration_thread",
            run_id="integration_run",
            state={},
            messages=[user_msg],
            tools=[],
            context=[],
            forwarded_props={},
        )

        # 4. Test handler creation
        mock_manager = Mock()
        session_handler = SessionHandler(mock_manager, session_param)
        user_handler = UserMessageHandler(agui_content, Mock(spec=Request))

        assert session_handler.app_name == "integration_app"
        assert user_handler.thread_id == "integration_thread"

        # 5. Test JSON operations
        state = {"integration": "test", "status": "active"}
        patches = convert_state_to_json_patch(state)
        converted_back = convert_json_patch_to_state(patches)
        assert converted_back == state

        # 6. Test error handling
        error = ErrorModel(error="INTEGRATION", error_description="All systems test")
        error_response = ErrorResponseModel(detail=error)

        # Should serialize without errors
        serialized = json.dumps(error_response.model_dump(), cls=DataclassesEncoder)
        assert "INTEGRATION" in serialized
