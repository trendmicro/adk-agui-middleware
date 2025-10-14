# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.sse_service module."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from ag_ui.core import BaseEvent, RunAgentInput
from ag_ui.encoder import EventEncoder
from fastapi import Request
from google.adk import Runner
from google.adk.agents import BaseAgent

from adk_agui_middleware.data_model.config import RunnerConfig
from adk_agui_middleware.data_model.context import ConfigContext
from adk_agui_middleware.data_model.session import SessionParameter
from adk_agui_middleware.service.sse_service import SSEService


class TestSSEService(unittest.TestCase):
    """Test cases for the SSEService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_agent = Mock(spec=BaseAgent)
        self.runner_config = RunnerConfig()

        # Create context config with mock functions
        async def mock_user_id(content, request):
            return "test_user"

        self.context_config = ConfigContext(app_name="test_app", user_id=mock_user_id)

        self.sse_service = SSEService(
            agent=self.mock_agent,
            runner_config=self.runner_config,
            config_context=self.context_config,
        )

        self.mock_agui_content = Mock(spec=RunAgentInput)
        self.mock_request = Mock(spec=Request)

    def test_init(self):
        """Test SSEService initialization."""
        self.assertEqual(self.sse_service.agent, self.mock_agent)
        self.assertEqual(self.sse_service.runner_config, self.runner_config)
        self.assertEqual(self.sse_service.config_context, self.context_config)
        self.assertIsNotNone(self.sse_service.session_manager)
        self.assertIsNotNone(self.sse_service.shutdown_handler)
        self.assertIsNotNone(self.sse_service.session_lock_handler)

    async def test_get_config_value_static_string(self):
        """Test _get_config_value with static string configuration."""
        result = await self.sse_service._get_config_value(
            "app_name", self.mock_agui_content, self.mock_request
        )

        self.assertEqual(result, "test_app")

    async def test_get_config_value_callable(self):
        """Test _get_config_value with callable configuration."""
        result = await self.sse_service._get_config_value(
            "user_id", self.mock_agui_content, self.mock_request
        )

        self.assertEqual(result, "test_user")

    async def test_extract_app_name(self):
        """Test extract_app_name method."""
        result = await self.sse_service.extract_app_name(
            self.mock_agui_content, self.mock_request
        )

        self.assertEqual(result, "test_app")

    async def test_extract_user_id(self):
        """Test extract_user_id method."""
        result = await self.sse_service.extract_user_id(
            self.mock_agui_content, self.mock_request
        )

        self.assertEqual(result, "test_user")

    async def test_extract_session_id_default(self):
        """Test extract_session_id with default implementation."""
        self.mock_agui_content.thread_id = "test_thread_123"

        result = await self.sse_service.extract_session_id(
            self.mock_agui_content, self.mock_request
        )

        self.assertEqual(result, "test_thread_123")

    async def test_extract_initial_state_none(self):
        """Test extract_initial_state when not configured."""
        result = await self.sse_service.extract_initial_state(
            self.mock_agui_content, self.mock_request
        )

        self.assertIsNone(result)

    async def test_extract_initial_state_with_custom_function(self):
        """Test extract_initial_state with custom extraction function."""

        async def custom_extract_state(content, request):
            return {"custom_key": "custom_value"}

        # Create new service with custom state extractor
        context_config = ConfigContext(
            user_id="test_user", extract_initial_state=custom_extract_state
        )

        service = SSEService(
            agent=self.mock_agent,
            runner_config=self.runner_config,
            config_context=context_config,
        )

        result = await service.extract_initial_state(
            self.mock_agui_content, self.mock_request
        )

        expected = {"custom_key": "custom_value"}
        self.assertEqual(result, expected)

    @patch("adk_agui_middleware.service.sse_service.convert_agui_event_to_str_fake_sse")
    def test_encoding_handler_success(self, mock_convert_fake_sse):
        """Test _encode_event_to_sse with successful encoding."""
        mock_convert_fake_sse.return_value = "data: encoded_event_string\n\n"
        mock_event = Mock(spec=BaseEvent)

        result = self.sse_service._encode_event_to_sse(mock_event)

        self.assertEqual(result, "data: encoded_event_string\n\n")
        mock_convert_fake_sse.assert_called_once_with(mock_event)

    @patch("adk_agui_middleware.service.sse_service.AGUIErrorEvent")
    @patch("adk_agui_middleware.service.sse_service.convert_agui_event_to_str_fake_sse")
    def test_encoding_handler_exception(self, mock_convert_fake_sse, mock_agui_error_event):
        """Test _encode_event_to_sse with encoding exception."""
        exception_obj = Exception("Encoding failed")
        mock_convert_fake_sse.side_effect = exception_obj
        mock_event = Mock(spec=BaseEvent)
        error_event = Mock(spec=BaseEvent)
        mock_agui_error_event.create_encoding_error_event.return_value = error_event
        # Mock the converter again for the error event
        mock_convert_fake_sse.side_effect = [exception_obj, "data: error_event_string\n\n"]

        result = self.sse_service._encode_event_to_sse(mock_event)

        self.assertEqual(result, "data: error_event_string\n\n")
        mock_agui_error_event.create_encoding_error_event.assert_called_once_with(exception_obj)

    @patch("adk_agui_middleware.service.sse_service.Runner")
    async def test_create_runner_new(self, mock_runner_class):
        """Test _create_runner creates new runner for new app."""
        mock_runner_instance = Mock(spec=Runner)
        mock_runner_class.return_value = mock_runner_instance

        app_name = "new_app"
        result = await self.sse_service._create_runner(app_name)

        self.assertEqual(result, mock_runner_instance)

        # Verify Runner was created with correct parameters
        # Note: agent should be deep copied, so we check the type instead of exact instance
        mock_runner_class.assert_called_once()
        call_kwargs = mock_runner_class.call_args[1]
        self.assertEqual(call_kwargs["app_name"], app_name)
        self.assertEqual(call_kwargs["session_service"], self.sse_service.session_manager.session_service)
        self.assertEqual(call_kwargs["artifact_service"], self.runner_config.get_artifact_service())
        self.assertEqual(call_kwargs["memory_service"], self.runner_config.get_memory_service())
        self.assertEqual(call_kwargs["credential_service"], self.runner_config.get_credential_service())
        self.assertEqual(call_kwargs["plugins"], self.runner_config.plugins)

    @patch("adk_agui_middleware.service.sse_service.Runner")
    async def test_create_runner_creates_new_instance(self, mock_runner_class):
        """Test _create_runner creates a new runner instance each time."""
        mock_runner_instance1 = Mock(spec=Runner)
        mock_runner_instance2 = Mock(spec=Runner)
        mock_runner_class.side_effect = [mock_runner_instance1, mock_runner_instance2]

        app_name = "test_app"
        result1 = await self.sse_service._create_runner(app_name)
        result2 = await self.sse_service._create_runner(app_name)

        # Each call should create a new instance
        self.assertEqual(result1, mock_runner_instance1)
        self.assertEqual(result2, mock_runner_instance2)
        self.assertEqual(mock_runner_class.call_count, 2)

    @patch("adk_agui_middleware.service.sse_service.AGUIUserHandler")
    @patch("adk_agui_middleware.service.sse_service.UserMessageHandler")
    @patch("adk_agui_middleware.service.sse_service.SessionHandler")
    async def test_get_runner(
        self,
        mock_session_handler_class,
        mock_user_message_handler_class,
        mock_agui_user_handler_class,
    ):
        """Test get_runner creates configured runner function."""
        # Setup mocks
        mock_user_handler_instance = Mock()
        mock_user_handler_instance.run = AsyncMock()
        mock_agui_user_handler_class.return_value = mock_user_handler_instance

        mock_user_message_handler = Mock()
        mock_user_message_handler_class.return_value = mock_user_message_handler

        mock_session_handler = Mock()
        mock_session_handler_class.return_value = mock_session_handler

        # Mock context extraction methods
        self.sse_service.extract_app_name = AsyncMock(return_value="test_app")
        self.sse_service.extract_user_id = AsyncMock(return_value="test_user")
        self.sse_service.extract_session_id = AsyncMock(return_value="test_session")
        self.sse_service.extract_initial_state = AsyncMock(
            return_value={"key": "value"}
        )

        # Mock runner creation
        mock_runner = Mock(spec=Runner)
        self.sse_service._create_runner = AsyncMock(return_value=mock_runner)

        # Get the runner function
        runner_func, in_out_handler = await self.sse_service.get_runner(
            self.mock_agui_content, self.mock_request
        )

        # Verify it's callable
        self.assertTrue(callable(runner_func))

        # Execute the runner function to test internal logic
        async for _ in runner_func():
            pass  # We're testing that it doesn't raise an exception

        # Verify handlers were created with correct parameters
        mock_user_message_handler_class.assert_called_once_with(
            self.mock_agui_content, self.mock_request, {"key": "value"}
        )

        mock_session_handler_class.assert_called_once()
        session_handler_call_args = mock_session_handler_class.call_args
        self.assertEqual(
            session_handler_call_args[1]["session_manager"],
            self.sse_service.session_manager,
        )

        # Check SessionParameter was created correctly
        session_param = session_handler_call_args[1]["session_parameter"]
        self.assertIsInstance(session_param, SessionParameter)
        self.assertEqual(session_param.app_name, "test_app")
        self.assertEqual(session_param.user_id, "test_user")
        self.assertEqual(session_param.session_id, "test_session")

    async def test_event_generator_success(self):
        """Test event_generator with successful event generation."""
        # Create mock events
        mock_event1 = Mock(spec=BaseEvent)
        mock_event2 = Mock(spec=BaseEvent)

        # Create mock runner that yields events
        async def mock_runner():
            yield mock_event1
            yield mock_event2

        # Create mock encoder
        mock_encoder = Mock(spec=EventEncoder)

        # Mock encoding handler to return encoded strings
        with patch.object(
            SSEService,
            "_encode_event_to_sse",
            side_effect=["encoded_event1", "encoded_event2"],
        ) as mock_encoding_handler:
            # Collect results from generator
            results = []
            async for encoded_event in self.sse_service.event_generator(
                mock_runner
            ):
                results.append(encoded_event)

            # Verify results
            expected = ["encoded_event1", "encoded_event2"]
            self.assertEqual(results, expected)

            # Verify encoding handler was called for each event
            self.assertEqual(mock_encoding_handler.call_count, 2)
            mock_encoding_handler.assert_any_call(mock_event1)
            mock_encoding_handler.assert_any_call(mock_event2)

    @patch("adk_agui_middleware.service.sse_service.AGUIEncoderError")
    async def test_event_generator_runner_exception(self, mock_agui_encoder_error):
        """Test event_generator handles runner exceptions."""

        # Create mock runner that raises exception
        async def mock_runner():
            raise Exception("Runner failed")

        mock_agui_encoder_error.create_agent_error_event.return_value = "error_encoded_event"

        # Collect results from generator
        results = []
        async for encoded_event in self.sse_service.event_generator(
            mock_runner
        ):
            results.append(encoded_event)

        # Should yield error event
        self.assertEqual(results, ["error_encoded_event"])
        mock_agui_encoder_error.create_agent_error_event.assert_called_once()

    async def test_event_generator_empty_runner(self):
        """Test event_generator with runner that yields no events."""

        # Create empty runner
        async def mock_runner():
            return
            yield  # Unreachable, just to make it a generator

        # Collect results
        results = []
        async for encoded_event in self.sse_service.event_generator(
            mock_runner
        ):
            results.append(encoded_event)

        # Should yield nothing
        self.assertEqual(results, [])

    def test_context_config_dynamic_values(self):
        """Test SSE service with dynamic context configuration."""

        async def dynamic_app_name(content, request):
            return f"app_{content.some_field}"

        async def dynamic_user_id(content, request):
            return request.headers.get("user-id", "default_user")

        context_config = ConfigContext(
            app_name=dynamic_app_name, user_id=dynamic_user_id
        )

        service = SSEService(
            agent=self.mock_agent,
            runner_config=self.runner_config,
            config_context=context_config,
        )

        # Verify service was created successfully
        self.assertEqual(service.config_context, context_config)

    @patch("adk_agui_middleware.service.sse_service.Runner")
    async def test_runner_creation_isolation(self, mock_runner_class):
        """Test that each _create_runner call creates independent runner instances."""
        mock_runner1 = Mock(spec=Runner)
        mock_runner2 = Mock(spec=Runner)
        mock_runner3 = Mock(spec=Runner)
        mock_runner_class.side_effect = [mock_runner1, mock_runner2, mock_runner3]

        app1_runner = await self.sse_service._create_runner("app1")
        app2_runner = await self.sse_service._create_runner("app2")

        # Should be different instances
        self.assertNotEqual(app1_runner, app2_runner)

        # Each call creates a new instance (no caching)
        app1_runner_again = await self.sse_service._create_runner("app1")
        self.assertNotEqual(app1_runner, app1_runner_again)

        # Verify all three runners were created
        self.assertEqual(mock_runner_class.call_count, 3)

    @patch("adk_agui_middleware.service.sse_service.SessionManager")
    def test_session_manager_initialization(self, mock_session_manager_class):
        """Test that SessionManager is initialized with correct session service."""
        mock_session_manager_instance = Mock()
        mock_session_manager_class.return_value = mock_session_manager_instance

        service = SSEService(
            agent=self.mock_agent,
            runner_config=self.runner_config,
            config_context=self.context_config,
        )

        mock_session_manager_class.assert_called_once_with(
            session_service=self.runner_config.session_service
        )
        self.assertEqual(service.session_manager, mock_session_manager_instance)

    async def test_extract_methods_with_none_values(self):
        """Test extract methods handle None values gracefully."""

        # Test with context config that might return None
        async def nullable_extractor(content, request):
            return None

        context_config = ConfigContext(
            user_id=nullable_extractor, extract_initial_state=nullable_extractor
        )

        service = SSEService(
            agent=self.mock_agent,
            runner_config=self.runner_config,
            config_context=context_config,
        )

        # These should handle None gracefully
        user_id = await service.extract_user_id(
            self.mock_agui_content, self.mock_request
        )
        initial_state = await service.extract_initial_state(
            self.mock_agui_content, self.mock_request
        )

        self.assertIsNone(user_id)
        self.assertIsNone(initial_state)


if __name__ == "__main__":
    unittest.main()
