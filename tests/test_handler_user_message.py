"""Unit tests for adk_agui_middleware.handler.user_message module."""

import json
import unittest
from unittest.mock import Mock, patch

from ag_ui.core import (
    AssistantMessage,
    FunctionCall,
    RunAgentInput,
    ToolCall,
    ToolMessage,
    UserMessage,
)
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
        """Test is_tool_result_submission returns True for tool messages."""
        tool_message = ToolMessage(
            id="1", role="tool", tool_call_id="call_1", content="tool result"
        )
        handler = self.create_handler(messages=[tool_message])

        self.assertTrue(handler.is_tool_result_submission)

    def test_is_tool_result_submission_false_user_message(self):
        """Test is_tool_result_submission returns False for user messages."""
        user_message = UserMessage(id="1", role="user", content="Hello")
        handler = self.create_handler(messages=[user_message])

        self.assertFalse(handler.is_tool_result_submission)

    def test_is_tool_result_submission_false_empty_messages(self):
        """Test is_tool_result_submission returns False for empty messages."""
        handler = self.create_handler(messages=[])

        self.assertFalse(handler.is_tool_result_submission)

    def test_is_tool_result_submission_mixed_messages(self):
        """Test is_tool_result_submission with mixed message types."""
        messages = [
            UserMessage(id="1", role="user", content="Hello"),
            ToolMessage(id="2", role="tool", tool_call_id="call_1", content="result"),
        ]
        handler = self.create_handler(messages=messages)

        self.assertTrue(handler.is_tool_result_submission)

    @patch("adk_agui_middleware.handler.user_message.record_warning_log")
    def test_parse_tool_content_empty_content(self, mock_warning):
        """Test _parse_tool_content with empty content."""
        result = UserMessageHandler._parse_tool_content("", "call_1")

        expected = {"success": True, "result": None}
        self.assertEqual(result, expected)
        mock_warning.assert_called_once()
        self.assertIn("Empty tool result content", mock_warning.call_args[0][0])

    @patch("adk_agui_middleware.handler.user_message.record_warning_log")
    def test_parse_tool_content_whitespace_only(self, mock_warning):
        """Test _parse_tool_content with whitespace-only content."""
        result = UserMessageHandler._parse_tool_content("   \n\t  ", "call_1")

        expected = {"success": True, "result": None}
        self.assertEqual(result, expected)
        mock_warning.assert_called_once()

    def test_parse_tool_content_valid_json(self):
        """Test _parse_tool_content with valid JSON."""
        content = json.dumps({"success": True, "data": "test"})
        result = UserMessageHandler._parse_tool_content(content, "call_1")

        expected = {"success": True, "data": "test"}
        self.assertEqual(result, expected)

    @patch("adk_agui_middleware.handler.user_message.record_error_log")
    def test_parse_tool_content_invalid_json(self, mock_error):
        """Test _parse_tool_content with invalid JSON."""
        invalid_json = "{ invalid json }"
        result = UserMessageHandler._parse_tool_content(invalid_json, "call_1")

        self.assertIn("error", result)
        self.assertIn("raw_content", result)
        self.assertIn("error_type", result)
        self.assertEqual(result["raw_content"], invalid_json)
        self.assertEqual(result["error_type"], "JSON_DECODE_ERROR")
        mock_error.assert_called_once()

    async def test_get_latest_message_user_message(self):
        """Test get_latest_message returns user message content."""
        user_message = UserMessage(id="1", role="user", content="Hello, how are you?")
        handler = self.create_handler(messages=[user_message])

        result = await handler.get_latest_message()

        self.assertIsInstance(result, types.Content)
        self.assertEqual(result.role, "user")
        self.assertEqual(len(result.parts), 1)
        self.assertEqual(result.parts[0].text, "Hello, how are you?")

    async def test_get_latest_message_multiple_messages(self):
        """Test get_latest_message returns latest user message."""
        messages = [
            UserMessage(id="1", role="user", content="First message"),
            UserMessage(id="2", role="user", content="Second message"),
            UserMessage(id="3", role="user", content="Latest message"),
        ]
        handler = self.create_handler(messages=messages)

        result = await handler.get_latest_message()

        self.assertEqual(result.parts[0].text, "Latest message")

    async def test_get_latest_message_empty_content(self):
        """Test get_latest_message skips messages with empty content."""
        messages = [
            UserMessage(id="1", role="user", content="Valid message"),
            UserMessage(id="2", role="user", content=""),
            UserMessage(id="3", role="user", content=None),
        ]
        handler = self.create_handler(messages=messages)

        result = await handler.get_latest_message()

        self.assertEqual(result.parts[0].text, "Valid message")

    async def test_get_latest_message_no_user_messages(self):
        """Test get_latest_message returns None when no user messages."""
        tool_message = ToolMessage(
            id="1", role="tool", tool_call_id="call_1", content="tool result"
        )
        handler = self.create_handler(messages=[tool_message])

        result = await handler.get_latest_message()

        self.assertIsNone(result)

    async def test_get_latest_message_empty_messages(self):
        """Test get_latest_message returns None for empty messages."""
        handler = self.create_handler(messages=[])

        result = await handler.get_latest_message()

        self.assertIsNone(result)

    @patch("adk_agui_middleware.handler.user_message.record_log")
    async def test_extract_tool_results_with_tool_message(self, mock_log):
        """Test extract_tool_results extracts tool results correctly."""
        # Create assistant message with tool calls
        tool_call = ToolCall(
            id="call_1", function=FunctionCall(name="test_function", arguments="{}")
        )
        assistant_msg = AssistantMessage(
            id="1", role="assistant", content="Using tool", tool_calls=[tool_call]
        )

        # Create tool message with result
        tool_msg = ToolMessage(
            id="2", role="tool", tool_call_id="call_1", content='{"success": true}'
        )

        messages = [assistant_msg, tool_msg]
        handler = self.create_handler(messages=messages)

        result = await handler.extract_tool_results()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tool_name"], "test_function")
        self.assertEqual(result[0]["message"], tool_msg)
        mock_log.assert_called_once()

    async def test_extract_tool_results_unknown_tool(self):
        """Test extract_tool_results with unknown tool call ID."""
        tool_msg = ToolMessage(
            id="1",
            role="tool",
            tool_call_id="unknown_call",
            content='{"result": "data"}',
        )
        handler = self.create_handler(messages=[tool_msg])

        result = await handler.extract_tool_results()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tool_name"], "unknown")

    async def test_extract_tool_results_no_tool_messages(self):
        """Test extract_tool_results returns empty list when no tool messages."""
        user_msg = UserMessage(id="1", role="user", content="Hello")
        handler = self.create_handler(messages=[user_msg])

        result = await handler.extract_tool_results()

        self.assertEqual(result, [])

    async def test_process_tool_results_not_tool_submission(self):
        """Test process_tool_results returns None for non-tool submissions."""
        user_msg = UserMessage(id="1", role="user", content="Hello")
        handler = self.create_handler(messages=[user_msg])

        result = await handler.process_tool_results()

        self.assertIsNone(result)

    async def test_process_tool_results_with_tool_submission(self):
        """Test process_tool_results processes tool results correctly."""
        # Setup tool call and result
        tool_call = ToolCall(
            id="call_1", function=FunctionCall(name="test_function", arguments="{}")
        )
        assistant_msg = AssistantMessage(
            id="1", role="assistant", content="", tool_calls=[tool_call]
        )
        tool_msg = ToolMessage(
            id="2",
            role="tool",
            tool_call_id="call_1",
            content='{"success": true, "data": "test"}',
        )

        messages = [assistant_msg, tool_msg]
        handler = self.create_handler(messages=messages)

        result = await handler.process_tool_results()

        self.assertIsInstance(result, types.Content)
        self.assertEqual(result.role, "user")
        self.assertEqual(len(result.parts), 1)

        function_response = result.parts[0].function_response
        self.assertEqual(function_response.id, "call_1")
        self.assertEqual(function_response.name, "test_function")
        self.assertEqual(function_response.response["success"], True)
        self.assertEqual(function_response.response["data"], "test")

    async def test_get_message_tool_result_priority(self):
        """Test get_message returns tool results when available."""
        # Setup messages with both user message and tool result
        tool_call = ToolCall(
            id="call_1", function=FunctionCall(name="test_function", arguments="{}")
        )
        messages = [
            UserMessage(id="1", role="user", content="User message"),
            AssistantMessage(
                id="2", role="assistant", content="", tool_calls=[tool_call]
            ),
            ToolMessage(
                id="3", role="tool", tool_call_id="call_1", content='{"result": "data"}'
            ),
        ]
        handler = self.create_handler(messages=messages)

        result = await handler.get_message()

        # Should return tool result, not user message
        self.assertIsInstance(result, types.Content)
        self.assertEqual(result.role, "user")
        self.assertTrue(hasattr(result.parts[0], "function_response"))

    async def test_get_message_user_message_fallback(self):
        """Test get_message returns user message when no tool results."""
        user_msg = UserMessage(id="1", role="user", content="Hello")
        handler = self.create_handler(messages=[user_msg])

        result = await handler.get_message()

        self.assertIsInstance(result, types.Content)
        self.assertEqual(result.role, "user")
        self.assertEqual(result.parts[0].text, "Hello")

    async def test_get_message_returns_none(self):
        """Test get_message returns None when no valid messages."""
        handler = self.create_handler(messages=[])

        result = await handler.get_message()

        self.assertIsNone(result)

    def test_multiple_tool_calls_mapping(self):
        """Test tool call mapping with multiple tool calls."""
        tool_call1 = ToolCall(
            id="call_1", function=FunctionCall(name="function_1", arguments="{}")
        )
        tool_call2 = ToolCall(
            id="call_2", function=FunctionCall(name="function_2", arguments="{}")
        )

        assistant_msg = AssistantMessage(
            id="1", role="assistant", content="", tool_calls=[tool_call1, tool_call2]
        )

        tool_msg = ToolMessage(
            id="2", role="tool", tool_call_id="call_2", content='{"result": "data"}'
        )

        messages = [assistant_msg, tool_msg]
        handler = self.create_handler(messages=messages)

        # Test the tool call mapping functionality
        agui_content = handler.agui_content
        tool_call_map = {
            tool_call.id: tool_call.function.name
            for msg in agui_content.messages
            if isinstance(msg, AssistantMessage) and msg.tool_calls
            for tool_call in msg.tool_calls
        }

        self.assertEqual(tool_call_map["call_1"], "function_1")
        self.assertEqual(tool_call_map["call_2"], "function_2")


if __name__ == "__main__":
    unittest.main()
