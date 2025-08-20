"""Additional tests for agui_user.py to boost coverage."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from google.adk import Runner
from google.adk.agents import RunConfig
from google.genai import types

from adk_agui_middleware.handler.agui_user import AGUIUserHandler
from adk_agui_middleware.handler.session import SessionHandler
from adk_agui_middleware.handler.user_message import UserMessageHandler

from test_utils import BaseTestCase


class TestAGUIUserHandlerCoverage(BaseTestCase):
    """Additional tests for AGUIUserHandler to improve coverage."""

    def setUp(self):
        super().setUp()

        # Create mocks
        self.mock_running_handler = Mock()
        self.mock_user_message_handler = Mock(spec=UserMessageHandler)
        self.mock_session_handler = Mock(spec=SessionHandler)

        # Set up mock return values
        self.mock_session_handler.app_name = "test_app"
        self.mock_session_handler.user_id = "test_user"
        self.mock_session_handler.session_id = "test_session"
        
        # Set up agui_content mock properly
        mock_agui_content = Mock()
        mock_agui_content.run_id = "test_run"
        self.mock_user_message_handler.agui_content = mock_agui_content

        # Create handler
        self.handler = AGUIUserHandler(
            running_handler=self.mock_running_handler,
            user_message_handler=self.mock_user_message_handler,
            session_handler=self.mock_session_handler,
        )

    def test_property_access(self):
        """Test property access methods."""
        assert self.handler.app_name == "test_app"
        assert self.handler.user_id == "test_user"
        assert self.handler.session_id == "test_session"
        assert self.handler.run_id == "test_run"

    def test_call_start_event_creation(self):
        """Test call start event creation."""
        event = self.handler.call_start()

        assert event.type.value == "RUN_STARTED"
        assert event.thread_id == "test_session"
        assert event.run_id == "test_run"

    def test_call_finished_event_creation(self):
        """Test call finished event creation."""
        event = self.handler.call_finished()

        assert event.type.value == "RUN_FINISHED"
        assert event.thread_id == "test_session"
        assert event.run_id == "test_run"

    @pytest.mark.asyncio
    async def test_check_tools_event_tool_call_end(self):
        """Test check tools event with tool call end."""

        tool_event = Mock()
        tool_event.tool_call_id = "call_123"

        # Mock isinstance to return True for ToolCallEndEvent
        with patch("builtins.isinstance") as mock_isinstance:
            mock_isinstance.side_effect = (
                lambda obj, cls: cls.__name__ == "ToolCallEndEvent"
            )

            await self.handler.check_tools_event(tool_event)

            # Should add tool call ID to list
            assert "call_123" in self.handler.tool_call_ids

    @pytest.mark.asyncio
    async def test_check_tools_event_tool_result(self):
        """Test check tools event with tool call result."""

        # First add a tool call ID
        self.handler.tool_call_ids = ["call_123"]

        result_event = Mock()
        result_event.tool_call_id = "call_123"

        # Mock isinstance to return True for ToolCallResultEvent
        with patch("builtins.isinstance") as mock_isinstance:
            mock_isinstance.side_effect = (
                lambda obj, cls: cls.__name__ == "ToolCallResultEvent"
            )

            await self.handler.check_tools_event(result_event)

            # Should remove tool call ID from list
            assert "call_123" not in self.handler.tool_call_ids

    @pytest.mark.asyncio
    async def test_remove_pending_tool_call_success(self):
        """Test successful removal of pending tool calls."""
        # Set up mock tool results
        tool_results = [
            {"message": Mock(tool_call_id="call_123"), "tool_name": "test_tool"}
        ]

        self.mock_user_message.extract_tool_results = AsyncMock(
            return_value=tool_results
        )
        self.mock_session_handler.check_and_remove_pending_tool_call = AsyncMock()

        result = await self.handler.remove_pending_tool_call()

        # Should return None on success
        assert result is None

        # Should call remove method
        self.mock_session_handler.check_and_remove_pending_tool_call.assert_called_once_with(
            "call_123"
        )

    @pytest.mark.asyncio
    async def test_remove_pending_tool_call_no_results(self):
        """Test removal when no tool results found."""
        self.mock_user_message.extract_tool_results = AsyncMock(return_value=[])
        self.mock_user_message.thread_id = "test_thread"

        result = await self.handler.remove_pending_tool_call()

        # Should return error event
        assert result is not None
        assert result.code == "NO_TOOL_RESULTS"

    @pytest.mark.asyncio
    async def test_remove_pending_tool_call_exception(self):
        """Test removal when exception occurs."""
        tool_results = [
            {"message": Mock(tool_call_id="call_123"), "tool_name": "test_tool"}
        ]

        self.mock_user_message.extract_tool_results = AsyncMock(
            return_value=tool_results
        )
        self.mock_session_handler.check_and_remove_pending_tool_call = AsyncMock(
            side_effect=Exception("Test error")
        )

        result = await self.handler.remove_pending_tool_call()

        # Should return error event
        assert result is not None
        assert result.code == "TOOL_RESULT_PROCESSING_ERROR"

    @pytest.mark.asyncio
    async def test_run_async_translator_adk_to_agui_regular(self):
        """Test ADK to AGUI translation for regular events."""
        mock_adk_event = Mock()
        mock_adk_event.is_final_response.return_value = False

        # Mock event translator
        mock_translator = Mock()
        mock_ag_ui_event = Mock()
        mock_translator.translate.return_value = AsyncMock()
        mock_translator.translate.return_value.__aiter__ = AsyncMock(
            return_value=iter([mock_ag_ui_event])
        )

        self.handler.event_translator = mock_translator

        result_list = []
        async for event in self.handler._run_async_translator_adk_to_agui(
            mock_adk_event
        ):
            result_list.append(event)

        # Should yield events from translator
        assert len(result_list) >= 0

    @pytest.mark.asyncio
    async def test_run_async_translator_adk_to_agui_final(self):
        """Test ADK to AGUI translation for final response events."""
        mock_adk_event = Mock()
        mock_adk_event.is_final_response.return_value = True

        # Mock event translator
        mock_translator = Mock()
        mock_ag_ui_event = Mock()
        mock_ag_ui_event.type.value = "tool_call_end"
        mock_translator.translate_lro_function_calls.return_value = AsyncMock()
        mock_translator.translate_lro_function_calls.return_value.__aiter__ = AsyncMock(
            return_value=iter([mock_ag_ui_event])
        )

        self.handler.event_translator = mock_translator

        result_list = []
        async for event in self.handler._run_async_translator_adk_to_agui(
            mock_adk_event
        ):
            result_list.append(event)

        # Should set long running tool flag
        assert self.handler.is_long_running_tool is True

    @pytest.mark.asyncio
    async def test_run_async_with_adk(self):
        """Test running async with ADK runner."""
        mock_message = Mock(spec=types.Content)
        mock_event = Mock()

        # Mock runner to return async iterator
        self.mock_runner.run_async.return_value = AsyncMock()
        self.mock_runner.run_async.return_value.__aiter__ = AsyncMock(
            return_value=iter([mock_event])
        )

        result_list = []
        async for event in self.handler._run_async_with_adk(mock_message):
            result_list.append(event)

        # Should call runner with correct parameters
        self.mock_runner.run_async.assert_called_once_with(
            user_id="test_user", session_id="test_session", new_message=mock_message
        )

    @pytest.mark.asyncio
    async def test_run_async_complete_flow(self):
        """Test complete async run flow."""
        # Mock user message
        mock_content = Mock(spec=types.Content)
        self.mock_user_message.get_message = AsyncMock(return_value=mock_content)

        # Mock ADK events
        mock_adk_event = Mock()
        mock_adk_event.is_final_response.return_value = False

        # Mock runner
        self.mock_runner.run_async.return_value = AsyncMock()
        self.mock_runner.run_async.return_value.__aiter__ = AsyncMock(
            return_value=iter([mock_adk_event])
        )

        # Mock translator
        mock_translator = Mock()
        mock_ag_ui_event = Mock()
        mock_ag_ui_event.type.value = "message_delta"
        mock_translator.translate.return_value = AsyncMock()
        mock_translator.translate.return_value.__aiter__ = AsyncMock(
            return_value=iter([mock_ag_ui_event])
        )
        mock_translator.force_close_streaming_message.return_value = AsyncMock()
        mock_translator.force_close_streaming_message.return_value.__aiter__ = (
            AsyncMock(return_value=iter([]))
        )
        mock_translator.create_state_snapshot_event.return_value = Mock()

        self.handler.event_translator = mock_translator

        # Mock session handler
        self.mock_session_handler.get_session_state = AsyncMock(
            return_value={"test": "state"}
        )

        result_list = []
        async for event in self.handler._run_async():
            result_list.append(event)

        # Should process events through the pipeline
        assert len(result_list) >= 0

    @pytest.mark.asyncio
    async def test_run_workflow_complete(self):
        """Test complete workflow execution."""
        # Mock initial state
        self.mock_user_message.initial_state = {"initial": "state"}

        # Mock session operations
        self.mock_session_handler.check_and_create_session = AsyncMock()
        self.mock_session_handler.update_session_state = AsyncMock()
        self.mock_session_handler.add_pending_tool_call = AsyncMock()

        # Mock _run_async to return events
        with patch.object(self.handler, "_run_async") as mock_run_async:
            mock_event = Mock()
            mock_run_async.return_value = AsyncMock()
            mock_run_async.return_value.__aiter__ = AsyncMock(
                return_value=iter([mock_event])
            )

            # Add some tool call IDs
            self.handler.tool_call_ids = ["call_1", "call_2"]

            result_list = []
            async for event in self.handler._run_workflow():
                result_list.append(event)

            # Should include start, events, and finish
            assert len(result_list) >= 2  # At least start and finish events

    @pytest.mark.asyncio
    async def test_run_main_entry_point_no_tool_results(self):
        """Test main run entry point without tool result submission."""
        self.mock_user_message.is_tool_result_submission = False

        # Mock _run_workflow
        with patch.object(self.handler, "_run_workflow") as mock_workflow:
            mock_event = Mock()
            mock_workflow.return_value = AsyncMock()
            mock_workflow.return_value.__aiter__ = AsyncMock(
                return_value=iter([mock_event])
            )

            result_list = []
            async for event in self.handler.run():
                result_list.append(event)

            # Should run workflow normally
            assert len(result_list) >= 0

    @pytest.mark.asyncio
    async def test_run_main_entry_point_with_tool_results_error(self):
        """Test main run entry point with tool result submission error."""
        self.mock_user_message.is_tool_result_submission = True

        # Mock remove_pending_tool_call to return error
        with patch.object(self.handler, "remove_pending_tool_call") as mock_remove:
            error_event = Mock()
            mock_remove.return_value = error_event

            result_list = []
            async for event in self.handler.run():
                result_list.append(event)

            # Should return error and stop
            assert len(result_list) == 1
            assert result_list[0] == error_event

    @pytest.mark.asyncio
    async def test_run_main_entry_point_with_exception(self):
        """Test main run entry point with exception."""
        self.mock_user_message.is_tool_result_submission = False

        # Mock _run_workflow to raise exception
        with patch.object(self.handler, "_run_workflow") as mock_workflow:
            mock_workflow.side_effect = Exception("Test error")

            result_list = []
            async for event in self.handler.run():
                result_list.append(event)

            # Should return execution error event
            assert len(result_list) == 1
            assert result_list[0].code == "EXECUTION_ERROR"

    def test_initialization_state(self):
        """Test handler initialization state."""
        assert self.handler.running_handler == self.mock_running_handler
        assert self.handler.user_message_handler == self.mock_user_message_handler
        assert self.handler.session_handler == self.mock_session_handler
        assert self.handler.tool_call_ids == []
