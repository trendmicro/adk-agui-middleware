"""Shared test utilities and fixtures for all test modules."""

from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock

from ag_ui.core import RunAgentInput, UserMessage, AssistantMessage, ToolMessage, ToolCall, FunctionCall
from fastapi import Request
from google.adk.sessions import Session
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode

from adk_agui_middleware.data_model.session import SessionParameter
from adk_agui_middleware.data_model.context import ContextConfig, RunnerConfig


class TestDataFactory:
    """Factory class for creating test data objects."""

    @staticmethod
    def create_session_parameter(
        app_name: str = "test_app",
        user_id: str = "test_user", 
        session_id: str = "test_session"
    ) -> SessionParameter:
        """Create a test SessionParameter instance."""
        return SessionParameter(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )

    @staticmethod
    def create_run_agent_input(
        thread_id: str = "test_thread",
        run_id: str = "test_run",
        messages: Optional[List[Any]] = None,
        state: Optional[Dict[str, Any]] = None
    ) -> RunAgentInput:
        """Create a test RunAgentInput instance."""
        return RunAgentInput(
            thread_id=thread_id,
            run_id=run_id,
            state=state or {},
            messages=messages or [],
            tools=[],
            context=[],
            forwarded_props={}
        )

    @staticmethod
    def create_user_message(
        message_id: str = "1",
        content: str = "Test message"
    ) -> UserMessage:
        """Create a test UserMessage instance."""
        return UserMessage(
            id=message_id,
            role="user",
            content=content
        )

    @staticmethod
    def create_assistant_message(
        message_id: str = "1",
        content: str = "Assistant response",
        tool_calls: Optional[List[ToolCall]] = None
    ) -> AssistantMessage:
        """Create a test AssistantMessage instance."""
        return AssistantMessage(
            id=message_id,
            role="assistant", 
            content=content,
            tool_calls=tool_calls or []
        )

    @staticmethod
    def create_tool_message(
        message_id: str = "1",
        tool_call_id: str = "call_1",
        content: str = '{"result": "success"}'
    ) -> ToolMessage:
        """Create a test ToolMessage instance."""
        return ToolMessage(
            id=message_id,
            role="tool",
            tool_call_id=tool_call_id,
            content=content
        )

    @staticmethod
    def create_tool_call(
        call_id: str = "call_1",
        function_name: str = "test_function",
        arguments: str = "{}"
    ) -> ToolCall:
        """Create a test ToolCall instance."""
        return ToolCall(
            id=call_id,
            function=FunctionCall(name=function_name, arguments=arguments)
        )

    @staticmethod
    def create_context_config(
        app_name: str = "test_app",
        user_id_func: Optional[Any] = None
    ) -> ContextConfig:
        """Create a test ContextConfig instance."""
        async def default_user_id(content, request):
            return "test_user"
            
        return ContextConfig(
            app_name=app_name,
            user_id=user_id_func or default_user_id
        )

    @staticmethod
    def create_runner_config(
        use_in_memory: bool = True,
        streaming_mode: StreamingMode = StreamingMode.SSE
    ) -> RunnerConfig:
        """Create a test RunnerConfig instance."""
        return RunnerConfig(
            use_in_memory_services=use_in_memory,
            run_config=RunConfig(streaming_mode=streaming_mode)
        )


class MockFactory:
    """Factory class for creating mock objects."""

    @staticmethod
    def create_request_mock(
        headers: Optional[Dict[str, str]] = None
    ) -> Mock:
        """Create a mock Request object."""
        mock_request = Mock(spec=Request)
        mock_request.headers = headers or {"accept": "text/event-stream"}
        return mock_request

    @staticmethod
    def create_session_mock(session_id: str = "test_session") -> Mock:
        """Create a mock Session object."""
        mock_session = Mock(spec=Session)
        mock_session.id = session_id
        return mock_session

    @staticmethod
    def create_async_session_manager_mock() -> Mock:
        """Create a mock SessionManager with async methods."""
        mock_manager = Mock()
        mock_manager.get_session = AsyncMock(return_value=None)
        mock_manager.get_session_state = AsyncMock(return_value={})
        mock_manager.check_and_create_session = AsyncMock()
        mock_manager.update_session_state = AsyncMock(return_value=True)
        return mock_manager


class TestAssertions:
    """Common test assertion helpers."""

    @staticmethod
    def assert_session_parameter_equal(
        param1: SessionParameter, 
        param2: SessionParameter
    ) -> None:
        """Assert two SessionParameter objects are equal."""
        assert param1.app_name == param2.app_name
        assert param1.user_id == param2.user_id
        assert param1.session_id == param2.session_id

    @staticmethod
    def assert_dict_contains_keys(
        target_dict: Dict[str, Any], 
        expected_keys: List[str]
    ) -> None:
        """Assert dictionary contains all expected keys."""
        for key in expected_keys:
            assert key in target_dict, f"Key '{key}' not found in dictionary"

    @staticmethod
    def assert_mock_called_with_args(
        mock_obj: Mock, 
        expected_args: tuple, 
        expected_kwargs: Optional[Dict[str, Any]] = None
    ) -> None:
        """Assert mock was called with specific arguments."""
        mock_obj.assert_called_once_with(*expected_args, **(expected_kwargs or {}))


import unittest

class BaseTestCase(unittest.TestCase):
    """Base test case with common setup and utilities."""

    def setUp(self):
        """Common setup for all test cases."""
        self.factory = TestDataFactory()
        self.mock_factory = MockFactory()
        self.assertions = TestAssertions()

    def create_test_data(self, data_type: str, **kwargs) -> Any:
        """Generic method to create test data."""
        factory_method = getattr(self.factory, f"create_{data_type}")
        return factory_method(**kwargs)

    def create_mock(self, mock_type: str, **kwargs) -> Mock:
        """Generic method to create mocks."""
        factory_method = getattr(self.mock_factory, f"create_{mock_type}_mock")
        return factory_method(**kwargs)


# Test data constants
TEST_CONSTANTS = {
    "DEFAULT_APP_NAME": "test_app",
    "DEFAULT_USER_ID": "test_user",
    "DEFAULT_SESSION_ID": "test_session",
    "DEFAULT_THREAD_ID": "test_thread",
    "DEFAULT_RUN_ID": "test_run",
    "TEST_TOOL_CALL_ID": "call_1",
    "TEST_FUNCTION_NAME": "test_function",
    "SUCCESS_RESPONSE": '{"success": true}',
    "ERROR_RESPONSE": '{"error": "test error"}',
    "EMPTY_STATE": {},
    "DEFAULT_HEADERS": {"accept": "text/event-stream"}
}


def parametrize_test_cases(test_cases: List[Dict[str, Any]]):
    """Decorator to parametrize test cases."""
    def decorator(test_func):
        def wrapper(self):
            for i, case in enumerate(test_cases):
                try:
                    test_func(self, **case)
                except Exception as e:
                    self.fail(f"Test case {i} failed with {case}: {str(e)}")
        return wrapper
    return decorator