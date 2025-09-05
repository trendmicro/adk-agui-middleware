"""Tests for AGUIUserHandler class."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from collections.abc import AsyncGenerator

from ag_ui.core import (
    BaseEvent,
    EventType,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    TextMessageContentEvent,
)

from adk_agui_middleware.handler.agui_user import AGUIUserHandler
from adk_agui_middleware.handler.running import RunningHandler
from adk_agui_middleware.handler.session import SessionHandler
from adk_agui_middleware.handler.user_message import UserMessageHandler
from adk_agui_middleware.event.error_event import AGUIErrorEvent


class TestAGUIUserHandler:
    """Test cases for AGUIUserHandler class."""

    @pytest.fixture
    def mock_running_handler(self):
        """Create mock running handler."""
        handler = Mock(spec=RunningHandler)
        handler.is_long_running_tool = False
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
        handler.is_tool_result_submission = False
        handler.extract_tool_results = AsyncMock()
        handler.get_message = AsyncMock()
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
        handler.check_and_remove_pending_tool_call = AsyncMock()
        handler.add_pending_tool_call = AsyncMock()
        handler.get_session_state = AsyncMock()
        return handler

    @pytest.fixture
    def agui_user_handler(self, mock_running_handler, mock_user_message_handler, mock_session_handler):
        """Create AGUIUserHandler instance with mocked dependencies."""
        return AGUIUserHandler(
            running_handler=mock_running_handler,
            user_message_handler=mock_user_message_handler,
            session_handler=mock_session_handler,
        )

    def test_init(self, mock_running_handler, mock_user_message_handler, mock_session_handler):
        """Test handler initialization."""
        handler = AGUIUserHandler(
            running_handler=mock_running_handler,
            user_message_handler=mock_user_message_handler,
            session_handler=mock_session_handler,
        )
        
        assert handler.running_handler == mock_running_handler
        assert handler.user_message_handler == mock_user_message_handler
        assert handler.session_handler == mock_session_handler
        assert handler.tool_call_ids == []

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

    def test_check_tools_event_tool_call_end(self, agui_user_handler):
        """Test tracking tool call end events."""
        tool_call_event = ToolCallEndEvent(
            type=EventType.TOOL_CALL_END,
            tool_call_id="tool-123"
        )
        
        agui_user_handler.check_tools_event(tool_call_event)
        
        assert "tool-123" in agui_user_handler.tool_call_ids

    def test_check_tools_event_tool_call_result(self, agui_user_handler):
        """Test removing tool call IDs when results are received."""
        # First add a tool call ID
        agui_user_handler.tool_call_ids.append("tool-123")
        
        tool_result_event = ToolCallResultEvent(
            type=EventType.TOOL_CALL_RESULT,
            tool_call_id="tool-123",
            message_id="msg-123",
            content="test result",
            role="tool"
        )
        
        agui_user_handler.check_tools_event(tool_result_event)
        
        assert "tool-123" not in agui_user_handler.tool_call_ids

    def test_check_tools_event_tool_call_result_not_in_list(self, agui_user_handler):
        """Test tool call result event when ID not in tracked list."""
        tool_result_event = ToolCallResultEvent(
            type=EventType.TOOL_CALL_RESULT,
            tool_call_id="unknown-tool",
            message_id="msg-123",
            content="test result",
            role="tool"
        )
        
        agui_user_handler.check_tools_event(tool_result_event)
        
        # Should not raise error, tool_call_ids should remain empty
        assert agui_user_handler.tool_call_ids == []

    def test_check_tools_event_other_event(self, agui_user_handler):
        """Test handling non-tool events."""
        other_event = TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            messageId="msg-123",
            delta="test message"
        )
        
        agui_user_handler.check_tools_event(other_event)
        
        # Should not affect tool_call_ids
        assert agui_user_handler.tool_call_ids == []

    @pytest.mark.asyncio
    async def test_remove_pending_tool_call_success(self, agui_user_handler, mock_user_message_handler, mock_session_handler):
        """Test successful pending tool call removal."""
        # Setup tool results
        tool_results = [
            {"message": Mock(tool_call_id="tool-1")},
            {"message": Mock(tool_call_id="tool-2")}
        ]
        mock_user_message_handler.extract_tool_results.return_value = tool_results
        
        with patch("adk_agui_middleware.handler.agui_user.record_log") as mock_record_log:
            result = await agui_user_handler.remove_pending_tool_call()
        
        assert result is None
        mock_session_handler.check_and_remove_pending_tool_call.assert_any_call(["tool-1"])
        mock_session_handler.check_and_remove_pending_tool_call.assert_any_call(["tool-2"])
        mock_record_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_pending_tool_call_no_results(self, agui_user_handler, mock_user_message_handler):
        """Test pending tool call removal with no tool results."""
        mock_user_message_handler.extract_tool_results.return_value = []
        
        with patch.object(AGUIErrorEvent, "create_no_tool_results_error") as mock_error:
            mock_error.return_value = Mock(spec=RunErrorEvent)
            result = await agui_user_handler.remove_pending_tool_call()
        
        assert result is not None
        mock_error.assert_called_once_with("test-thread-id")

    @pytest.mark.asyncio
    async def test_remove_pending_tool_call_exception(self, agui_user_handler, mock_user_message_handler, mock_session_handler):
        """Test pending tool call removal with exception."""
        tool_results = [{"message": Mock(tool_call_id="tool-1")}]
        mock_user_message_handler.extract_tool_results.return_value = tool_results
        mock_session_handler.check_and_remove_pending_tool_call.side_effect = Exception("Test error")
        
        with patch.object(AGUIErrorEvent, "create_tool_processing_error_event") as mock_error:
            mock_error.return_value = Mock(spec=RunErrorEvent)
            result = await agui_user_handler.remove_pending_tool_call()
        
        assert result is not None
        mock_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_async_normal_flow(self, agui_user_handler, mock_running_handler, mock_user_message_handler, mock_session_handler):
        """Test normal async execution flow."""
        # Setup mock events
        adk_event = Mock()
        agui_event = ToolCallEndEvent(type=EventType.TOOL_CALL_END, tool_call_id="tool-1")
        
        async def mock_adk_generator(*args, **kwargs):
            yield adk_event
        
        async def mock_agui_generator(event):
            yield agui_event
        
        async def mock_force_close():
            yield Mock()
        
        # Mock the async calls properly
        mock_user_message_handler.get_message = AsyncMock(return_value=Mock())
        mock_running_handler.run_async_with_adk = mock_adk_generator
        mock_running_handler.run_async_with_agui = Mock(side_effect=mock_agui_generator)
        mock_running_handler.is_long_running_tool = False
        mock_running_handler.force_close_streaming_message = mock_force_close
        mock_session_handler.get_session_state = AsyncMock(return_value={"final": "state"})
        mock_running_handler.create_state_snapshot_event = AsyncMock(return_value=Mock())
        
        events = []
        async for event in agui_user_handler._run_async():
            events.append(event)
        
        assert len(events) == 3  # 1 agui event + 1 force close + 1 state snapshot
        assert "tool-1" in agui_user_handler.tool_call_ids

    @pytest.mark.asyncio
    async def test_run_async_long_running_tool(self, agui_user_handler, mock_running_handler, mock_user_message_handler):
        """Test async execution with long running tool."""
        async def mock_empty_adk_generator(*args, **kwargs):
            if False:
                yield  # Make it an async generator but never yield
        
        async def mock_empty_agui_generator(event):
            if False:
                yield  # Make it an async generator but never yield
        
        mock_user_message_handler.get_message = AsyncMock(return_value=Mock())
        mock_running_handler.run_async_with_adk = mock_empty_adk_generator
        mock_running_handler.run_async_with_agui = Mock(side_effect=mock_empty_agui_generator)
        mock_running_handler.is_long_running_tool = True
        mock_running_handler.force_close_streaming_message = Mock()
        
        events = []
        async for event in agui_user_handler._run_async():
            events.append(event)
        
        # Should return early, no force close or state snapshot
        mock_running_handler.force_close_streaming_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_async_no_final_state(self, agui_user_handler, mock_running_handler, mock_user_message_handler, mock_session_handler):
        """Test async execution with no final state."""
        async def mock_empty_adk_generator(*args, **kwargs):
            if False:
                yield  # Make it an async generator but never yield
        
        async def mock_empty_agui_generator(event):
            if False:
                yield  # Make it an async generator but never yield
        
        async def mock_empty_force_close():
            if False:
                yield  # Make it an async generator but never yield
        
        mock_user_message_handler.get_message = AsyncMock(return_value=Mock())
        mock_running_handler.run_async_with_adk = mock_empty_adk_generator
        mock_running_handler.run_async_with_agui = Mock(side_effect=mock_empty_agui_generator)
        mock_running_handler.is_long_running_tool = False
        mock_running_handler.force_close_streaming_message = mock_empty_force_close
        mock_session_handler.get_session_state = AsyncMock(return_value=None)
        mock_running_handler.create_state_snapshot_event = AsyncMock(return_value=None)
        
        events = []
        async for event in agui_user_handler._run_async():
            events.append(event)
        
        # Should call create_state_snapshot_event but not yield since it returns None
        mock_running_handler.create_state_snapshot_event.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_run_workflow(self, agui_user_handler, mock_session_handler, mock_user_message_handler):
        """Test complete workflow execution."""
        mock_user_message_handler.initial_state = {"initial": "state"}
        
        # Mock _run_async to return some events
        async def mock_run_async_generator():
            yield Mock()
            yield Mock()
        
        with patch.object(agui_user_handler, "_run_async", return_value=mock_run_async_generator()):
            # Add some tool call IDs to test pending tool call addition
            agui_user_handler.tool_call_ids = ["tool-1", "tool-2"]
            
            events = []
            async for event in agui_user_handler._run_workflow():
                events.append(event)
        
        # Should have start event + 2 from _run_async + finish event
        assert len(events) == 4
        assert isinstance(events[0], RunStartedEvent)
        assert isinstance(events[-1], RunFinishedEvent)
        
        # Verify session operations
        mock_session_handler.check_and_create_session.assert_called_once_with({"initial": "state"})
        mock_session_handler.update_session_state.assert_called_once_with({"initial": "state"})
        mock_session_handler.add_pending_tool_call.assert_called_once_with(["tool-1", "tool-2"])

    @pytest.mark.asyncio
    async def test_run_with_tool_result_submission_error(self, agui_user_handler, mock_user_message_handler):
        """Test run with tool result submission that has error."""
        mock_user_message_handler.is_tool_result_submission = True
        
        error_event = Mock(spec=RunErrorEvent)
        with patch.object(agui_user_handler, "remove_pending_tool_call", return_value=error_event):
            events = []
            async for event in agui_user_handler.run():
                events.append(event)
        
        assert len(events) == 1
        assert events[0] == error_event

    @pytest.mark.asyncio
    async def test_run_with_tool_result_submission_success(self, agui_user_handler, mock_user_message_handler):
        """Test run with successful tool result submission."""
        mock_user_message_handler.is_tool_result_submission = True
        
        async def mock_workflow_generator():
            yield Mock()
            yield Mock()
        
        with patch.object(agui_user_handler, "remove_pending_tool_call", return_value=None):
            with patch.object(agui_user_handler, "_run_workflow", return_value=mock_workflow_generator()):
                events = []
                async for event in agui_user_handler.run():
                    events.append(event)
        
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_run_normal_flow(self, agui_user_handler, mock_user_message_handler):
        """Test normal run execution flow."""
        mock_user_message_handler.is_tool_result_submission = False
        
        async def mock_workflow_generator():
            yield Mock()
            yield Mock()
        
        with patch.object(agui_user_handler, "_run_workflow", return_value=mock_workflow_generator()):
            events = []
            async for event in agui_user_handler.run():
                events.append(event)
        
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_run_with_exception(self, agui_user_handler, mock_user_message_handler):
        """Test run with exception handling."""
        mock_user_message_handler.is_tool_result_submission = False
        
        test_exception = Exception("Test error")
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


async def mock_agui_generator_func(event):
    """Mock function that returns an async generator for a single event."""
    yield Mock(spec=BaseEvent)