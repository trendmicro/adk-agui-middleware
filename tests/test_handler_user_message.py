"""Unit tests for adk_agui_middleware.handler.user_message module."""

import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from ag_ui.core import AssistantMessage, RunAgentInput, ToolCall, ToolMessage, UserMessage
from fastapi import Request
from google.genai import types

from adk_agui_middleware.handler.user_message import UserMessageHandler


class TestUserMessageHandler(unittest.TestCase):
    """Test cases for the UserMessageHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_request = Mock(spec=Request)
        self.mock_agui_content = Mock(spec=RunAgentInput)
        self.mock_agui_content.thread_id = "test_thread_123"
        self.mock_agui_content.messages = []
        
        self.handler = UserMessageHandler(
            agui_content=self.mock_agui_content,
            request=self.mock_request,
            initial_state={"test_key": "test_value"}
        )

    def test_init(self):
        """Test UserMessageHandler initialization."""
        self.assertEqual(self.handler.agui_content, self.mock_agui_content)
        self.assertEqual(self.handler.request, self.mock_request)
        self.assertEqual(self.handler.initial_state, {"test_key": "test_value"})

    def test_init_without_initial_state(self):
        """Test UserMessageHandler initialization without initial state."""
        handler = UserMessageHandler(
            agui_content=self.mock_agui_content,
            request=self.mock_request
        )
        
        self.assertIsNone(handler.initial_state)

    def test_thread_id_property(self):
        """Test thread_id property returns correct value."""
        self.assertEqual(self.handler.thread_id, "test_thread_123")

    def test_initial_state_property(self):
        """Test initial_state property returns correct value."""
        self.assertEqual(self.handler.initial_state, {"test_key": "test_value"})

    def test_is_tool_result_submission_true(self):
        """Test is_tool_result_submission returns True for tool message."""
        tool_message = Mock()
        tool_message.role = "tool"
        self.mock_agui_content.messages = [tool_message]
        
        self.assertTrue(self.handler.is_tool_result_submission)

    def test_is_tool_result_submission_false(self):
        """Test is_tool_result_submission returns False for non-tool message."""
        user_message = Mock()
        user_message.role = "user"
        self.mock_agui_content.messages = [user_message]
        
        self.assertFalse(self.handler.is_tool_result_submission)

    def test_is_tool_result_submission_empty_messages(self):
        """Test is_tool_result_submission returns False for empty messages."""
        self.mock_agui_content.messages = []
        
        self.assertFalse(self.handler.is_tool_result_submission)

    def test_is_tool_result_submission_multiple_messages(self):
        """Test is_tool_result_submission checks only the latest message."""
        user_message = Mock()
        user_message.role = "user"
        tool_message = Mock()
        tool_message.role = "tool"
        
        self.mock_agui_content.messages = [user_message, tool_message]
        
        self.assertTrue(self.handler.is_tool_result_submission)

    @patch('adk_agui_middleware.handler.user_message.record_warning_log')
    def test_parse_tool_content_empty_content(self, mock_warning_log):
        """Test _parse_tool_content with empty content."""
        result = UserMessageHandler._parse_tool_content("", "tool123")
        
        expected = {"success": True, "result": None}
        self.assertEqual(result, expected)
        mock_warning_log.assert_called_once()

    @patch('adk_agui_middleware.handler.user_message.record_warning_log')
    def test_parse_tool_content_whitespace_only(self, mock_warning_log):
        """Test _parse_tool_content with whitespace-only content."""
        result = UserMessageHandler._parse_tool_content("   \n\t  ", "tool123")
        
        expected = {"success": True, "result": None}
        self.assertEqual(result, expected)
        mock_warning_log.assert_called_once()

    def test_parse_tool_content_valid_json(self):
        """Test _parse_tool_content with valid JSON content."""
        content = '{"result": "success", "data": {"value": 42}}'
        
        result = UserMessageHandler._parse_tool_content(content, "tool123")
        
        expected = {"result": "success", "data": {"value": 42}}
        self.assertEqual(result, expected)

    @patch('adk_agui_middleware.handler.user_message.record_error_log')
    def test_parse_tool_content_invalid_json(self, mock_error_log):
        """Test _parse_tool_content with invalid JSON content."""
        content = '{"invalid": json content}'
        
        result = UserMessageHandler._parse_tool_content(content, "tool123")
        
        self.assertIn("error", result)
        self.assertIn("Invalid JSON in tool result", result["error"])
        self.assertEqual(result["raw_content"], content)
        self.assertEqual(result["error_type"], "JSON_DECODE_ERROR")
        mock_error_log.assert_called_once()

    def test_parse_tool_content_simple_string(self):
        """Test _parse_tool_content with simple string (invalid JSON)."""
        content = "simple text result"
        
        with patch('adk_agui_middleware.handler.user_message.record_error_log'):
            result = UserMessageHandler._parse_tool_content(content, "tool123")
        
        self.assertIn("error", result)
        self.assertEqual(result["raw_content"], content)

    async def test_get_latest_message_no_messages(self):
        """Test get_latest_message with no messages."""
        self.mock_agui_content.messages = []
        
        result = await self.handler.get_latest_message()
        
        self.assertIsNone(result)

    async def test_get_latest_message_user_message(self):
        """Test get_latest_message with user message."""
        user_msg = Mock()
        user_msg.role = "user"
        user_msg.content = "Hello, how are you?"
        self.mock_agui_content.messages = [user_msg]
        
        result = await self.handler.get_latest_message()
        
        self.assertIsNotNone(result)
        self.assertEqual(result.role, "user")
        self.assertEqual(len(result.parts), 1)
        self.assertEqual(result.parts[0].text, "Hello, how are you?")

    async def test_get_latest_message_multiple_user_messages(self):
        """Test get_latest_message returns most recent user message."""
        user_msg1 = Mock()
        user_msg1.role = "user"
        user_msg1.content = "First message"
        
        user_msg2 = Mock()
        user_msg2.role = "user"
        user_msg2.content = "Latest message"
        
        assistant_msg = Mock()
        assistant_msg.role = "assistant"
        assistant_msg.content = "Assistant response"
        
        self.mock_agui_content.messages = [user_msg1, assistant_msg, user_msg2]
        
        result = await self.handler.get_latest_message()
        
        self.assertEqual(result.parts[0].text, "Latest message")

    async def test_get_latest_message_empty_content(self):
        """Test get_latest_message ignores user messages with empty content."""
        user_msg1 = Mock()
        user_msg1.role = "user"
        user_msg1.content = ""
        
        user_msg2 = Mock()
        user_msg2.role = "user"
        user_msg2.content = "Valid message"
        
        self.mock_agui_content.messages = [user_msg2, user_msg1]
        
        result = await self.handler.get_latest_message()
        
        self.assertEqual(result.parts[0].text, "Valid message")

    async def test_get_latest_message_no_user_messages(self):
        """Test get_latest_message with no user messages."""
        assistant_msg = Mock()
        assistant_msg.role = "assistant"
        assistant_msg.content = "Assistant response"
        
        tool_msg = Mock()
        tool_msg.role = "tool"
        
        self.mock_agui_content.messages = [assistant_msg, tool_msg]
        
        result = await self.handler.get_latest_message()
        
        self.assertIsNone(result)

    async def test_extract_tool_results_no_tool_messages(self):
        """Test extract_tool_results with no tool messages."""
        user_msg = Mock()
        user_msg.role = "user"
        self.mock_agui_content.messages = [user_msg]
        
        result = await self.handler.extract_tool_results()
        
        self.assertEqual(result, [])

    @patch('adk_agui_middleware.handler.user_message.record_log')
    async def test_extract_tool_results_with_tool_message(self, mock_log):
        """Test extract_tool_results with tool message and tool call mapping."""
        # Create tool call
        tool_call = ToolCall(
            id="tool_call_123",
            type="function",
            function=Mock(name="test_function")
        )
        
        # Create assistant message with tool call
        assistant_msg = AssistantMessage(
            id="assistant_1",
            role="assistant",
            content="Using tool",
            tool_calls=[tool_call]
        )
        
        # Create tool message
        tool_msg = ToolMessage(
            id="tool_1",
            role="tool",
            content="Tool result",
            tool_call_id="tool_call_123"
        )
        
        self.mock_agui_content.messages = [assistant_msg, tool_msg]
        
        result = await self.handler.extract_tool_results()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tool_name"], "test_function")
        self.assertEqual(result[0]["message"], tool_msg)
        mock_log.assert_called_once()

    async def test_extract_tool_results_unknown_tool_name(self):
        """Test extract_tool_results with unknown tool call ID."""
        tool_msg = ToolMessage(
            id="tool_1",
            role="tool",
            content="Tool result",
            tool_call_id="unknown_call_id"
        )
        
        self.mock_agui_content.messages = [tool_msg]
        
        result = await self.handler.extract_tool_results()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tool_name"], "unknown")

    async def test_extract_tool_results_multiple_tool_messages(self):
        """Test extract_tool_results returns only most recent tool message."""
        tool_msg1 = ToolMessage(
            id="tool_1",
            role="tool",
            content="First result",
            tool_call_id="call_1"
        )
        
        tool_msg2 = ToolMessage(
            id="tool_2",
            role="tool", 
            content="Latest result",
            tool_call_id="call_2"
        )
        
        self.mock_agui_content.messages = [tool_msg1, tool_msg2]
        
        result = await self.handler.extract_tool_results()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["message"], tool_msg2)

    async def test_process_tool_results_not_tool_submission(self):
        """Test process_tool_results when not a tool result submission."""
        user_msg = Mock()
        user_msg.role = "user"
        self.mock_agui_content.messages = [user_msg]
        
        result = await self.handler.process_tool_results()
        
        self.assertIsNone(result)

    async def test_process_tool_results_with_valid_json(self):
        """Test process_tool_results with valid JSON tool result."""
        # Mock extract_tool_results to return tool result
        tool_msg = ToolMessage(
            id="tool_1",
            role="tool",
            content='{"result": "success", "data": 42}',
            tool_call_id="call_123"
        )
        
        self.handler.extract_tool_results = AsyncMock(return_value=[{
            "tool_name": "test_tool",
            "message": tool_msg
        }])
        
        # Mock is_tool_result_submission to return True
        with patch.object(self.handler, 'is_tool_result_submission', True):
            result = await self.handler.process_tool_results()
        
        self.assertIsNotNone(result)
        self.assertEqual(result.role, "user")
        self.assertEqual(len(result.parts), 1)
        
        function_response = result.parts[0].function_response
        self.assertEqual(function_response.id, "call_123")
        self.assertEqual(function_response.name, "test_tool")
        self.assertEqual(function_response.response["result"], "success")

    async def test_process_tool_results_with_invalid_json(self):
        """Test process_tool_results with invalid JSON tool result."""
        tool_msg = ToolMessage(
            id="tool_1",
            role="tool",
            content="invalid json",
            tool_call_id="call_123"
        )
        
        self.handler.extract_tool_results = AsyncMock(return_value=[{
            "tool_name": "test_tool",
            "message": tool_msg
        }])
        
        with patch.object(self.handler, 'is_tool_result_submission', True):
            result = await self.handler.process_tool_results()
        
        function_response = result.parts[0].function_response
        self.assertIn("error", function_response.response)

    async def test_process_tool_results_multiple_tools(self):
        """Test process_tool_results with multiple tool results."""
        tool_msg1 = ToolMessage(
            id="tool_1", role="tool", content='{"result": 1}', tool_call_id="call_1"
        )
        tool_msg2 = ToolMessage(
            id="tool_2", role="tool", content='{"result": 2}', tool_call_id="call_2"
        )
        
        self.handler.extract_tool_results = AsyncMock(return_value=[
            {"tool_name": "tool1", "message": tool_msg1},
            {"tool_name": "tool2", "message": tool_msg2}
        ])
        
        with patch.object(self.handler, 'is_tool_result_submission', True):
            result = await self.handler.process_tool_results()
        
        self.assertEqual(len(result.parts), 2)
        self.assertEqual(result.parts[0].function_response.name, "tool1")
        self.assertEqual(result.parts[1].function_response.name, "tool2")

    async def test_get_message_tool_result_submission(self):
        """Test get_message returns tool results for tool submission."""
        mock_tool_content = Mock(spec=types.Content)
        
        with patch.object(self.handler, 'process_tool_results', 
                         AsyncMock(return_value=mock_tool_content)):
            result = await self.handler.get_message()
        
        self.assertEqual(result, mock_tool_content)

    async def test_get_message_user_message(self):
        """Test get_message returns user message for non-tool submission."""
        mock_user_content = Mock(spec=types.Content)
        
        with patch.object(self.handler, 'process_tool_results', 
                         AsyncMock(return_value=None)):
            with patch.object(self.handler, 'get_latest_message',
                             AsyncMock(return_value=mock_user_content)):
                result = await self.handler.get_message()
        
        self.assertEqual(result, mock_user_content)

    async def test_get_message_no_content(self):
        """Test get_message returns None when no content available."""
        with patch.object(self.handler, 'process_tool_results', 
                         AsyncMock(return_value=None)):
            with patch.object(self.handler, 'get_latest_message',
                             AsyncMock(return_value=None)):
                result = await self.handler.get_message()
        
        self.assertIsNone(result)

    def test_initial_state_property_setter(self):
        """Test that initial_state can be modified."""
        new_state = {"new_key": "new_value"}
        self.handler.initial_state = new_state
        
        self.assertEqual(self.handler.initial_state, new_state)

    async def test_integration_full_conversation_flow(self):
        """Test integration of full conversation flow."""
        # Setup a complete conversation
        tool_call = ToolCall(
            id="integrate_call",
            type="function", 
            function=Mock(name="integration_tool")
        )
        
        user_msg = UserMessage(id="u1", role="user", content="User question")
        assistant_msg = AssistantMessage(
            id="a1", role="assistant", content="Using tool", tool_calls=[tool_call]
        )
        tool_msg = ToolMessage(
            id="t1", role="tool", content='{"success": true}', tool_call_id="integrate_call"
        )
        
        self.mock_agui_content.messages = [user_msg, assistant_msg, tool_msg]
        
        # Test tool result processing
        tool_result = await self.handler.process_tool_results()
        self.assertIsNotNone(tool_result)
        self.assertEqual(tool_result.role, "user")
        
        # Test that get_message returns tool result
        message = await self.handler.get_message()
        self.assertEqual(message, tool_result)

    async def test_edge_case_malformed_messages(self):
        """Test handling of malformed or incomplete messages."""
        # Create mock messages with missing attributes
        incomplete_msg = Mock()
        incomplete_msg.role = "user"
        incomplete_msg.content = None  # Missing content
        
        self.mock_agui_content.messages = [incomplete_msg]
        
        result = await self.handler.get_latest_message()
        self.assertIsNone(result)

    def test_static_method_independence(self):
        """Test that static methods work independently of instance state."""
        # Test _parse_tool_content as static method
        result = UserMessageHandler._parse_tool_content('{"test": "data"}', "static_test")
        self.assertEqual(result, {"test": "data"})


if __name__ == '__main__':
    unittest.main()