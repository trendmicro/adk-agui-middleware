# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.handler.user_message module."""

import unittest
from unittest.mock import AsyncMock, Mock

from ag_ui.core import RunAgentInput, ToolMessage, UserMessage
from fastapi import Request
from google.genai import types

from adk_agui_middleware.handler.user_message import UserMessageHandler


class TestUserMessageHandler(unittest.TestCase):
    """Test cases for the UserMessageHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.request = Mock(spec=Request)
        self.initial_state = {"key": "value"}

    def create_handler(self, messages=None, thread_id="test_thread"):
        """Helper method to create a UserMessageHandler instance."""
        agui_content = RunAgentInput(
            thread_id=thread_id,
            run_id="test_run",
            state={},
            messages=messages or [],
            tools=[],
            context=[],
            forwarded_props={},
        )
        return UserMessageHandler(
            agui_content=agui_content,
            request=self.request,
            initial_state=self.initial_state,
        )

    def test_init(self):
        """Test UserMessageHandler initialization."""
        handler = self.create_handler()

        self.assertEqual(handler.thread_id, "test_thread")
        self.assertEqual(handler.request, self.request)
        self.assertEqual(handler.initial_state, self.initial_state)

    def test_thread_id_property(self):
        """Test thread_id property."""
        handler = self.create_handler(thread_id="custom_thread")
        self.assertEqual(handler.thread_id, "custom_thread")

    def test_is_tool_result_submission_true(self):
        """Test is_tool_result_submission returns ToolMessage for tool messages."""
        tool_message = ToolMessage(
            id="1", role="tool", tool_call_id="call_1", content="tool result"
        )
        handler = self.create_handler(messages=[tool_message])

        result = handler.is_tool_result_submission
        self.assertIsInstance(result, ToolMessage)
        self.assertEqual(result, tool_message)

    def test_is_tool_result_submission_false_user_message(self):
        """Test is_tool_result_submission returns None for user messages."""
        user_message = UserMessage(id="1", role="user", content="Hello")
        handler = self.create_handler(messages=[user_message])

        result = handler.is_tool_result_submission
        self.assertIsNone(result)

    def test_is_tool_result_submission_false_empty_messages(self):
        """Test is_tool_result_submission returns None for empty messages."""
        handler = self.create_handler(messages=[])

        result = handler.is_tool_result_submission
        self.assertIsNone(result)

    def test_is_tool_result_submission_mixed_messages(self):
        """Test is_tool_result_submission with mixed message types."""
        messages = [
            UserMessage(id="1", role="user", content="Hello"),
            ToolMessage(id="2", role="tool", tool_call_id="call_1", content="result"),
        ]
        handler = self.create_handler(messages=messages)

        result = handler.is_tool_result_submission
        self.assertIsInstance(result, ToolMessage)
        self.assertEqual(result.tool_call_id, "call_1")

    async def test_init_with_convert_function(self):
        """Test init method with convert_run_agent_input function."""
        convert_mock = AsyncMock()
        converted_content = Mock()
        convert_mock.return_value = converted_content

        handler = self.create_handler()
        handler.convert_run_agent_input = convert_mock

        tool_call_info = {"tool_1": "function_1"}
        await handler.init(tool_call_info)

        convert_mock.assert_called_once_with(handler.agui_content, tool_call_info)
        self.assertEqual(handler.agui_content, converted_content)

    async def test_init_without_convert_function(self):
        """Test init method without convert_run_agent_input function."""
        handler = self.create_handler()
        original_content = handler.agui_content

        tool_call_info = {"tool_1": "function_1"}
        await handler.init(tool_call_info)

        # Content should remain unchanged
        self.assertEqual(handler.agui_content, original_content)

    def test_get_latest_message_user_message(self):
        """Test get_latest_message returns user message content."""
        user_message = UserMessage(id="1", role="user", content="Hello, how are you?")
        handler = self.create_handler(messages=[user_message])

        result = handler.get_latest_message()

        self.assertIsInstance(result, types.Content)
        self.assertEqual(result.role, "user")
        self.assertEqual(len(result.parts), 1)
        self.assertEqual(result.parts[0].text, "Hello, how are you?")

    def test_get_latest_message_multiple_messages(self):
        """Test get_latest_message returns latest user message."""
        messages = [
            UserMessage(id="1", role="user", content="First message"),
            UserMessage(id="2", role="user", content="Second message"),
            UserMessage(id="3", role="user", content="Latest message"),
        ]
        handler = self.create_handler(messages=messages)

        result = handler.get_latest_message()

        self.assertEqual(result.parts[0].text, "Latest message")

    def test_get_latest_message_empty_content(self):
        """Test get_latest_message skips messages with empty content."""
        messages = [
            UserMessage(id="2", role="user", content=""),
            UserMessage(id="1", role="user", content="Valid message"),
        ]
        handler = self.create_handler(messages=messages)

        result = handler.get_latest_message()

        # The implementation goes in reverse order, so the last valid message is "Valid message"
        self.assertIsNotNone(result)
        self.assertEqual(result.parts[0].text, "Valid message")

    def test_get_latest_message_no_user_messages(self):
        """Test get_latest_message returns None when no user messages."""
        tool_message = ToolMessage(
            id="1", role="tool", tool_call_id="call_1", content="tool result"
        )
        handler = self.create_handler(messages=[tool_message])

        result = handler.get_latest_message()

        self.assertIsNone(result)

    def test_get_latest_message_empty_messages(self):
        """Test get_latest_message returns None for empty messages."""
        handler = self.create_handler(messages=[])

        result = handler.get_latest_message()

        self.assertIsNone(result)

    def test_convert_run_agent_input_property(self):
        """Test that convert_run_agent_input is properly stored."""
        convert_func = AsyncMock()

        agui_content = RunAgentInput(
            thread_id="test_thread",
            run_id="test_run",
            state={},
            messages=[],
            tools=[],
            context=[],
            forwarded_props={},
        )

        handler = UserMessageHandler(
            agui_content=agui_content,
            request=self.request,
            initial_state=self.initial_state,
            convert_run_agent_input=convert_func,
        )

        self.assertEqual(handler.convert_run_agent_input, convert_func)

    def test_handler_attributes(self):
        """Test that all handler attributes are properly set."""
        handler = self.create_handler()

        # Test all attributes exist
        self.assertTrue(hasattr(handler, "agui_content"))
        self.assertTrue(hasattr(handler, "request"))
        self.assertTrue(hasattr(handler, "initial_state"))
        self.assertTrue(hasattr(handler, "convert_run_agent_input"))

        # Test attribute values
        self.assertEqual(handler.request, self.request)
        self.assertEqual(handler.initial_state, self.initial_state)
        self.assertIsNone(handler.convert_run_agent_input)


if __name__ == "__main__":
    unittest.main()