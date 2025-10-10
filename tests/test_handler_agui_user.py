# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Tests for AGUIUserHandler class."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from ag_ui.core import (BaseEvent, EventType, RunErrorEvent, RunFinishedEvent,
                        RunStartedEvent, TextMessageContentEvent,
                        ToolCallEndEvent, ToolCallResultEvent)
from google.adk.events import Event
from google.genai import types

from adk_agui_middleware.event.error_event import AGUIErrorEvent
from adk_agui_middleware.handler.agui_user import AGUIUserHandler
from adk_agui_middleware.handler.queue import QueueHandler
from adk_agui_middleware.handler.running import RunningHandler
from adk_agui_middleware.handler.session import SessionHandler
from adk_agui_middleware.handler.user_message import UserMessageHandler


class TestAGUIUserHandler:
    """Test cases for AGUIUserHandler class."""

    @pytest.fixture
    def mock_running_handler(self):
        """Create mock running handler."""
        handler = Mock(spec=RunningHandler)
        handler.set_long_running_tool_ids = Mock()
        handler.run_async_with_adk = AsyncMock()
        handler.run_async_with_agui = AsyncMock()
        handler.force_close_streaming_message = AsyncMock()
        handler.create_state_snapshot_event = AsyncMock()
        return handler

    @pytest.fixture
    def mock_user_message_handler(self):
        """Create mock user message handler."""
        handler = Mock(spec=UserMessageHandler)
        handler.agui_content = Mock()
        handler.agui_content.run_id = "test-run-id"
        handler.thread_id = "test-thread-id"
        handler.initial_state = {"test": "state"}
        handler.is_tool_result_submission = None
        handler.init = AsyncMock()
        handler.get_latest_message = AsyncMock()
        return handler

    @pytest.fixture
    def mock_session_handler(self):
        """Create mock session handler."""
        handler = Mock(spec=SessionHandler)
        handler.app_name = "test-app"
        handler.user_id = "test-user"
        handler.session_id = "test-session"
        handler.check_and_create_session = AsyncMock()
        handler.update_session_state = AsyncMock()
        handler.overwrite_pending_tool_calls = AsyncMock()
        handler.get_pending_tool_calls = AsyncMock(return_value={})
        handler.get_session_state = AsyncMock()
        return handler

    @pytest.fixture
    def mock_queue_handler(self):
        """Create mock queue handler."""
        handler = Mock(spec=QueueHandler)
        mock_adk_queue = Mock()
        mock_agui_queue = Mock()
        handler.get_adk_queue = Mock(return_value=mock_adk_queue)
        handler.get_agui_queue = Mock(return_value=mock_agui_queue)
        return handler

    @pytest.fixture
    def agui_user_handler(self, mock_running_handler, mock_user_message_handler, mock_session_handler, mock_queue_handler):
        """Create AGUIUserHandler instance with mocked dependencies."""
        return AGUIUserHandler(
            running_handler=mock_running_handler,
            user_message_handler=mock_user_message_handler,
            session_handler=mock_session_handler,
            queue_handler=mock_queue_handler,
        )

    def test_init(self, mock_running_handler, mock_user_message_handler, mock_session_handler, mock_queue_handler):
        """Test handler initialization."""
        handler = AGUIUserHandler(
            running_handler=mock_running_handler,
            user_message_handler=mock_user_message_handler,
            session_handler=mock_session_handler,
            queue_handler=mock_queue_handler,
        )

        assert handler.running_handler == mock_running_handler
        assert handler.user_message_handler == mock_user_message_handler
        assert handler.session_handler == mock_session_handler
        assert handler.queue_handler == mock_queue_handler
        assert handler.tool_call_info == {}
        assert handler.input_message is None

    def test_properties(self, agui_user_handler):
        """Test property accessors."""
        assert agui_user_handler.app_name == "test-app"
        assert agui_user_handler.user_id == "test-user"
        assert agui_user_handler.session_id == "test-session"
        assert agui_user_handler.run_id == "test-run-id"

    def test_call_start(self, agui_user_handler):
        """Test run started event creation."""
        event = agui_user_handler.call_start()

        assert isinstance(event, RunStartedEvent)
        assert event.type == EventType.RUN_STARTED
        assert event.thread_id == "test-session"
        assert event.run_id == "test-run-id"

    def test_call_finished(self, agui_user_handler):
        """Test run finished event creation."""
        event = agui_user_handler.call_finished()

        assert isinstance(event, RunFinishedEvent)
        assert event.type == EventType.RUN_FINISHED
        assert event.thread_id == "test-session"
        assert event.run_id == "test-run-id"

    def test_check_is_long_running_tool_no_long_running_ids(self, agui_user_handler):
        """Test check_is_long_running_tool with no long-running tool IDs."""
        adk_event = Mock(spec=Event)
        adk_event.long_running_tool_ids = None

        result = agui_user_handler.check_is_long_running_tool(adk_event)

        assert result is False

    def test_check_is_long_running_tool_empty_long_running_ids(self, agui_user_handler):
        """Test check_is_long_running_tool with empty long-running tool IDs."""
        adk_event = Mock(spec=Event)
        adk_event.long_running_tool_ids = []

        result = agui_user_handler.check_is_long_running_tool(adk_event)

        assert result is False

    def test_check_is_long_running_tool_with_matching_tool(self, agui_user_handler):
        """Test check_is_long_running_tool with matching tool call."""
        # Create mock function call
        func_call = Mock()
        func_call.id = "tool-123"
        func_call.name = "test_function"

        adk_event = Mock(spec=Event)
        adk_event.long_running_tool_ids = ["tool-123"]
        adk_event.get_function_calls.return_value = [func_call]

        result = agui_user_handler.check_is_long_running_tool(adk_event)

        assert result is True
        assert agui_user_handler.tool_call_info["tool-123"] == "test_function"

    def test_check_is_long_running_tool_no_matching_tool(self, agui_user_handler):
        """Test check_is_long_running_tool with no matching tool call."""
        # Create mock function call that doesn't match
        func_call = Mock()
        func_call.id = "tool-456"
        func_call.name = "other_function"

        adk_event = Mock(spec=Event)
        adk_event.long_running_tool_ids = ["tool-123"]
        adk_event.get_function_calls.return_value = [func_call]

        result = agui_user_handler.check_is_long_running_tool(adk_event)

        assert result is False
        assert "tool-456" not in agui_user_handler.tool_call_info

    @pytest.mark.asyncio
    async def test_async_init(self, agui_user_handler, mock_session_handler, mock_user_message_handler, mock_running_handler):
        """Test async initialization."""
        mock_session_handler.get_pending_tool_calls.return_value = {"tool-1": "function_1"}

        await agui_user_handler._async_init()

        mock_session_handler.get_pending_tool_calls.assert_called_once()
        mock_running_handler.set_long_running_tool_ids.assert_called_once_with({"tool-1": "function_1"})
        mock_user_message_handler.init.assert_called_once_with({"tool-1": "function_1"})
        assert agui_user_handler.tool_call_info == {"tool-1": "function_1"}

    @pytest.mark.asyncio
    async def test_process_tool_result_with_tool_message(self, agui_user_handler, mock_user_message_handler, mock_session_handler):
        """Test process_tool_result with tool message."""
        mock_tool_message = Mock()
        mock_tool_message.tool_call_id = "tool-123"

        mock_user_message_handler.is_tool_result_submission = mock_tool_message
        agui_user_handler.tool_call_info = {"tool-123": "test_function"}

        with patch("adk_agui_middleware.handler.agui_user.convert_agui_tool_message_to_adk_function_response") as mock_convert:
            # Create a proper Part with FunctionResponse that will satisfy the Content validation
            function_response = types.FunctionResponse(
                id="tool-123",
                name="test_function",
                response={"result": "success"}
            )
            mock_part = types.Part(function_response=function_response)
            mock_convert.return_value = mock_part

            result = await agui_user_handler.process_tool_result()

        assert isinstance(result, types.Content)
        assert result.role == "user"
        assert len(result.parts) == 1
        mock_session_handler.overwrite_pending_tool_calls.assert_called_once()
        mock_convert.assert_called_once_with(mock_tool_message, "test_function")

    @pytest.mark.asyncio
    async def test_process_tool_result_no_tool_message(self, agui_user_handler, mock_user_message_handler):
        """Test process_tool_result with no tool message."""
        mock_user_message_handler.is_tool_result_submission = None
        mock_user_message_handler.get_latest_message.return_value = Mock()

        result = await agui_user_handler.process_tool_result()

        mock_user_message_handler.get_latest_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_tool_result_no_tool_call_name(self, agui_user_handler, mock_user_message_handler):
        """Test process_tool_result with tool message but no matching tool call name."""
        mock_tool_message = Mock()
        mock_tool_message.tool_call_id = "unknown-tool"

        mock_user_message_handler.is_tool_result_submission = mock_tool_message
        agui_user_handler.tool_call_info = {}  # Empty tool call info

        with patch.object(AGUIErrorEvent, "create_no_tool_results_error") as mock_error:
            mock_error.return_value = Mock(spec=RunErrorEvent)
            result = await agui_user_handler.process_tool_result()

        assert isinstance(result, Mock)
        mock_error.assert_called_once_with("test-session")

    @pytest.mark.asyncio
    async def test_set_user_input_success(self, agui_user_handler):
        """Test set_user_input with successful processing."""
        mock_content = Mock(spec=types.Content)

        with patch.object(agui_user_handler, "process_tool_result", return_value=mock_content):
            result = await agui_user_handler.set_user_input()

        assert result is None
        assert agui_user_handler.input_message == mock_content

    @pytest.mark.asyncio
    async def test_set_user_input_with_error(self, agui_user_handler):
        """Test set_user_input with error from processing."""
        mock_error = Mock(spec=RunErrorEvent)

        with patch.object(agui_user_handler, "process_tool_result", return_value=mock_error):
            result = await agui_user_handler.set_user_input()

        assert result == mock_error
        assert agui_user_handler.input_message is None

    @pytest.mark.asyncio
    async def test_run_workflow(self, agui_user_handler, mock_session_handler, mock_user_message_handler):
        """Test complete workflow execution."""
        mock_user_message_handler.initial_state = {"initial": "state"}

        # Mock the queue iterators to return some events
        async def mock_agui_queue_iterator():
            yield Mock(spec=BaseEvent)
            yield Mock(spec=BaseEvent)

        # Mock the _run_async_with_adk and _run_async_with_agui methods
        async def mock_run_async_with_adk():
            return

        async def mock_run_async_with_agui():
            return

        agui_user_handler.agui_queue.get_iterator = Mock(return_value=mock_agui_queue_iterator())

        with patch.object(agui_user_handler, "_run_async_with_adk", side_effect=mock_run_async_with_adk):
            with patch.object(agui_user_handler, "_run_async_with_agui", side_effect=mock_run_async_with_agui):
                agui_user_handler.tool_call_info = {"tool-1": "function_1"}

                events = []
                async for event in agui_user_handler._run_workflow():
                    events.append(event)

        # Should have start event + 2 from queue iterator + finish event
        assert len(events) == 4
        assert isinstance(events[0], RunStartedEvent)
        assert isinstance(events[-1], RunFinishedEvent)

        # Verify session operations
        mock_session_handler.check_and_create_session.assert_called_once_with({"initial": "state"})
        mock_session_handler.update_session_state.assert_called_once_with({"initial": "state"})
        mock_session_handler.overwrite_pending_tool_calls.assert_called_once_with({"tool-1": "function_1"})

    @pytest.mark.asyncio
    async def test_run_success(self, agui_user_handler):
        """Test successful run execution."""
        async def mock_workflow_generator():
            yield Mock(spec=BaseEvent)
            yield Mock(spec=BaseEvent)

        with patch.object(agui_user_handler, "_async_init") as mock_init:
            with patch.object(agui_user_handler, "set_user_input", return_value=None):
                with patch.object(agui_user_handler, "_run_workflow", return_value=mock_workflow_generator()):
                    events = []
                    async for event in agui_user_handler.run():
                        events.append(event)

        assert len(events) == 2
        mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_input_error(self, agui_user_handler):
        """Test run with input processing error."""
        mock_error = Mock(spec=RunErrorEvent)

        with patch.object(agui_user_handler, "_async_init"):
            with patch.object(agui_user_handler, "set_user_input", return_value=mock_error):
                events = []
                async for event in agui_user_handler.run():
                    events.append(event)

        assert len(events) == 1
        assert events[0] == mock_error

    @pytest.mark.asyncio
    async def test_run_with_exception(self, agui_user_handler):
        """Test run with exception handling."""
        test_exception = Exception("Test error")

        with patch.object(agui_user_handler, "_async_init"):
            with patch.object(agui_user_handler, "set_user_input", return_value=None):
                with patch.object(agui_user_handler, "_run_workflow", side_effect=test_exception):
                    with patch.object(AGUIErrorEvent, "create_execution_error_event") as mock_error:
                        mock_error.return_value = Mock(spec=RunErrorEvent)

                        events = []
                        async for event in agui_user_handler.run():
                            events.append(event)

        assert len(events) == 1
        mock_error.assert_called_once_with(test_exception)


async def async_generator(items):
    """Helper function to create async generator."""
    for item in items:
        yield item