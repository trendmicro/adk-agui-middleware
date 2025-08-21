"""Unit tests for adk_agui_middleware.handler.session module."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from google.adk.sessions import Session

from adk_agui_middleware.data_model.session import SessionParameter
from adk_agui_middleware.handler.session import SessionHandler
from adk_agui_middleware.manager.session import SessionManager


class TestSessionHandler(unittest.TestCase):
    """Test cases for the SessionHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session_manager = Mock(spec=SessionManager)
        self.session_parameter = SessionParameter(
            app_name="test_app", user_id="test_user", session_id="test_session"
        )
        self.session_handler = SessionHandler(
            session_manager=self.mock_session_manager,
            session_parameter=self.session_parameter,
        )

    def test_init(self):
        """Test SessionHandler initialization."""
        self.assertEqual(
            self.session_handler.session_manager, self.mock_session_manager
        )
        self.assertEqual(self.session_handler.session_parameter, self.session_parameter)

    def test_app_name_property(self):
        """Test app_name property returns session parameter app name."""
        self.assertEqual(self.session_handler.app_name, "test_app")

    def test_user_id_property(self):
        """Test user_id property returns session parameter user ID."""
        self.assertEqual(self.session_handler.user_id, "test_user")

    def test_session_id_property(self):
        """Test session_id property returns session parameter session ID."""
        self.assertEqual(self.session_handler.session_id, "test_session")

    def test_get_pending_tool_calls_dict(self):
        """Test get_pending_tool_calls_dict static method."""
        pending_calls = ["call1", "call2", "call3"]
        result = SessionHandler.get_pending_tool_calls_dict(pending_calls)

        expected = {"pending_tool_calls": pending_calls}
        self.assertEqual(result, expected)

    def test_get_pending_tool_calls_dict_empty(self):
        """Test get_pending_tool_calls_dict with empty list."""
        result = SessionHandler.get_pending_tool_calls_dict([])

        expected = {"pending_tool_calls": []}
        self.assertEqual(result, expected)

    async def test_get_session(self):
        """Test get_session method."""
        mock_session = Mock(spec=Session)
        self.mock_session_manager.get_session = AsyncMock(return_value=mock_session)

        result = await self.session_handler.get_session()

        self.assertEqual(result, mock_session)
        self.mock_session_manager.get_session.assert_called_once_with(
            self.session_parameter
        )

    async def test_get_session_none(self):
        """Test get_session returns None when session not found."""
        self.mock_session_manager.get_session = AsyncMock(return_value=None)

        result = await self.session_handler.get_session()

        self.assertIsNone(result)

    async def test_get_session_state(self):
        """Test get_session_state method."""
        mock_state = {"key": "value", "pending_tool_calls": []}
        self.mock_session_manager.get_session_state = AsyncMock(return_value=mock_state)

        result = await self.session_handler.get_session_state()

        self.assertEqual(result, mock_state)
        self.mock_session_manager.get_session_state.assert_called_once_with(
            self.session_parameter
        )

    async def test_check_and_create_session(self):
        """Test check_and_create_session method."""
        mock_session = Mock(spec=Session)
        initial_state = {"initial": "state"}
        self.mock_session_manager.check_and_create_session = AsyncMock(
            return_value=mock_session
        )

        result = await self.session_handler.check_and_create_session(initial_state)

        self.assertEqual(result, mock_session)
        self.mock_session_manager.check_and_create_session.assert_called_once_with(
            session_parameter=self.session_parameter, initial_state=initial_state
        )

    async def test_check_and_create_session_no_initial_state(self):
        """Test check_and_create_session without initial state."""
        mock_session = Mock(spec=Session)
        self.mock_session_manager.check_and_create_session = AsyncMock(
            return_value=mock_session
        )

        result = await self.session_handler.check_and_create_session()

        self.assertEqual(result, mock_session)
        self.mock_session_manager.check_and_create_session.assert_called_once_with(
            session_parameter=self.session_parameter, initial_state=None
        )

    async def test_update_session_state_success(self):
        """Test update_session_state method success."""
        state_updates = {"updated": "value"}
        self.mock_session_manager.update_session_state = AsyncMock(return_value=True)

        result = await self.session_handler.update_session_state(state_updates)

        self.assertTrue(result)
        self.mock_session_manager.update_session_state.assert_called_once_with(
            session_parameter=self.session_parameter, state_updates=state_updates
        )

    async def test_update_session_state_failure(self):
        """Test update_session_state method failure."""
        self.mock_session_manager.update_session_state = AsyncMock(return_value=False)

        result = await self.session_handler.update_session_state(None)

        self.assertFalse(result)

    @patch("adk_agui_middleware.handler.session.record_warning_log")
    @patch("adk_agui_middleware.handler.session.record_log")
    async def test_check_and_remove_pending_tool_call_not_found(
        self, mock_log, mock_warning
    ):
        """Test check_and_remove_pending_tool_call when tool call not in pending list."""
        self.session_handler.get_pending_tool_calls = AsyncMock(
            return_value=["other_call"]
        )

        await self.session_handler.check_and_remove_pending_tool_call("missing_call")

        mock_warning.assert_called_once()
        self.assertIn("No pending tool calls found", mock_warning.call_args[0][0])

    @patch("adk_agui_middleware.handler.session.record_log")
    async def test_check_and_remove_pending_tool_call_success(self, mock_log):
        """Test successful removal of pending tool call."""
        pending_calls = ["call1", "call2", "call3"]
        self.session_handler.get_pending_tool_calls = AsyncMock(
            return_value=pending_calls
        )
        self.mock_session_manager.update_session_state = AsyncMock(return_value=True)

        await self.session_handler.check_and_remove_pending_tool_call("call2")

        # Verify the call was removed from the list
        self.assertEqual(pending_calls, ["call1", "call3"])

        # Verify session state was updated
        self.mock_session_manager.update_session_state.assert_called_once_with(
            session_parameter=self.session_parameter,
            state_updates={"pending_tool_calls": ["call1", "call3"]},
        )

    @patch("adk_agui_middleware.handler.session.record_error_log")
    @patch("adk_agui_middleware.handler.session.record_log")
    async def test_add_pending_tool_call_success(self, mock_log, mock_error):
        """Test successful addition of pending tool call."""
        existing_state = {"pending_tool_calls": ["call1"]}
        self.mock_session_manager.get_session_state = AsyncMock(
            return_value=existing_state
        )
        self.mock_session_manager.update_session_state = AsyncMock(return_value=True)

        await self.session_handler.add_pending_tool_call("call2")

        # Verify session state was updated with new call
        self.mock_session_manager.update_session_state.assert_called_once_with(
            self.session_parameter,
            state_updates={"pending_tool_calls": ["call1", "call2"]},
        )
        mock_error.assert_not_called()

    @patch("adk_agui_middleware.handler.session.record_error_log")
    @patch("adk_agui_middleware.handler.session.record_log")
    async def test_add_pending_tool_call_already_exists(self, mock_log, mock_error):
        """Test adding tool call that already exists in pending list."""
        existing_state = {"pending_tool_calls": ["call1", "call2"]}
        self.mock_session_manager.get_session_state = AsyncMock(
            return_value=existing_state
        )

        await self.session_handler.add_pending_tool_call("call2")

        # Should not update session state since call already exists
        self.mock_session_manager.update_session_state.assert_not_called()
        mock_error.assert_not_called()

    @patch("adk_agui_middleware.handler.session.record_error_log")
    @patch("adk_agui_middleware.handler.session.record_log")
    async def test_add_pending_tool_call_no_existing_calls(self, mock_log, mock_error):
        """Test adding tool call when no pending calls exist."""
        existing_state = {}
        self.mock_session_manager.get_session_state = AsyncMock(
            return_value=existing_state
        )
        self.mock_session_manager.update_session_state = AsyncMock(return_value=True)

        await self.session_handler.add_pending_tool_call("call1")

        # Should create new pending calls list
        self.mock_session_manager.update_session_state.assert_called_once_with(
            self.session_parameter, state_updates={"pending_tool_calls": ["call1"]}
        )

    @patch("adk_agui_middleware.handler.session.record_error_log")
    async def test_add_pending_tool_call_exception(self, mock_error):
        """Test add_pending_tool_call handles exceptions."""
        self.mock_session_manager.get_session_state = AsyncMock(
            side_effect=Exception("Test error")
        )

        await self.session_handler.add_pending_tool_call("call1")

        mock_error.assert_called_once()

    @patch("adk_agui_middleware.handler.session.record_warning_log")
    async def test_get_pending_tool_calls_success(self, mock_warning):
        """Test successful retrieval of pending tool calls."""
        session_state = {
            "test_session": "session_data",
            "pending_tool_calls": ["call1", "call2"],
        }
        self.mock_session_manager.get_session_state = AsyncMock(
            return_value=session_state
        )

        result = await self.session_handler.get_pending_tool_calls()

        self.assertEqual(result, ["call1", "call2"])
        mock_warning.assert_not_called()

    @patch("adk_agui_middleware.handler.session.record_error_log")
    async def test_get_pending_tool_calls_no_session(self, mock_error):
        """Test get_pending_tool_calls when session state has no pending calls."""
        session_state = {"other_key": "data"}
        self.mock_session_manager.get_session_state = AsyncMock(
            return_value=session_state
        )

        result = await self.session_handler.get_pending_tool_calls()

        # Should return empty list when pending_tool_calls key is not in state
        self.assertEqual(result, [])
        mock_error.assert_not_called()

    @patch("adk_agui_middleware.handler.session.record_error_log")
    async def test_get_pending_tool_calls_no_pending_calls(self, mock_error):
        """Test get_pending_tool_calls when no pending calls in session."""
        session_state = {"other_key": "other_value"}
        self.mock_session_manager.get_session_state = AsyncMock(
            return_value=session_state
        )

        result = await self.session_handler.get_pending_tool_calls()

        self.assertEqual(result, [])
        mock_error.assert_not_called()

    @patch("adk_agui_middleware.handler.session.record_error_log")
    async def test_get_pending_tool_calls_exception(self, mock_error):
        """Test get_pending_tool_calls handles exceptions."""
        self.mock_session_manager.get_session_state = AsyncMock(
            side_effect=Exception("Test error")
        )

        result = await self.session_handler.get_pending_tool_calls()

        self.assertEqual(result, [])  # Should return empty list, not None
        mock_error.assert_called_once()

    @patch("adk_agui_middleware.handler.session.record_error_log")
    @patch("adk_agui_middleware.handler.session.record_log")
    async def test_add_pending_tool_call_update_failure(self, mock_log, mock_error):
        """Test add_pending_tool_call when session state update fails."""
        existing_state = {"pending_tool_calls": ["call1"]}
        self.mock_session_manager.get_session_state = AsyncMock(
            return_value=existing_state
        )
        self.mock_session_manager.update_session_state = AsyncMock(return_value=False)

        await self.session_handler.add_pending_tool_call("call2")

        # Verify session state update was attempted but failed
        self.mock_session_manager.update_session_state.assert_called_once_with(
            self.session_parameter,
            state_updates={"pending_tool_calls": ["call1", "call2"]},
        )
        # No success log should be called when update fails
        success_calls = [call for call in mock_log.call_args_list 
                        if "Added tool call" in str(call)]
        self.assertEqual(len(success_calls), 0)

    @patch("adk_agui_middleware.handler.session.record_error_log")
    @patch("adk_agui_middleware.handler.session.record_log")
    async def test_add_pending_tool_call_get_state_exception(self, mock_log, mock_error):
        """Test add_pending_tool_call handles get_session_state exception."""
        self.session_handler.get_pending_tool_calls = AsyncMock(
            side_effect=Exception("Database error")
        )

        await self.session_handler.add_pending_tool_call("call1")

        mock_error.assert_called_once()
        self.assertIn("Failed to add pending tool call", mock_error.call_args[0][0])

    @patch("adk_agui_middleware.handler.session.record_error_log")
    @patch("adk_agui_middleware.handler.session.record_log")
    async def test_add_pending_tool_call_update_state_exception(self, mock_log, mock_error):
        """Test add_pending_tool_call handles update_session_state exception."""
        existing_state = {"pending_tool_calls": []}
        self.mock_session_manager.get_session_state = AsyncMock(
            return_value=existing_state
        )
        self.mock_session_manager.update_session_state = AsyncMock(
            side_effect=Exception("Update failed")
        )

        await self.session_handler.add_pending_tool_call("call1")

        mock_error.assert_called_once()
        self.assertIn("Failed to add pending tool call", mock_error.call_args[0][0])

    @patch("adk_agui_middleware.handler.session.record_log")
    async def test_check_and_remove_pending_tool_call_update_failure(self, mock_log):
        """Test check_and_remove_pending_tool_call when session state update fails."""
        pending_calls = ["call1", "call2", "call3"]
        self.session_handler.get_pending_tool_calls = AsyncMock(
            return_value=pending_calls
        )
        self.mock_session_manager.update_session_state = AsyncMock(return_value=False)

        await self.session_handler.check_and_remove_pending_tool_call("call2")

        # Verify the call was removed from the list
        self.assertEqual(pending_calls, ["call1", "call3"])

        # Verify session state was updated
        self.mock_session_manager.update_session_state.assert_called_once_with(
            session_parameter=self.session_parameter,
            state_updates={"pending_tool_calls": ["call1", "call3"]},
        )
        
        # Verify final log message indicates failure
        final_log_call = mock_log.call_args_list[-1]
        self.assertIn("False", str(final_log_call))

    @patch("adk_agui_middleware.handler.session.record_warning_log")
    @patch("adk_agui_middleware.handler.session.record_log")
    async def test_check_and_remove_pending_tool_call_empty_list(self, mock_log, mock_warning):
        """Test check_and_remove_pending_tool_call with empty pending calls list."""
        self.session_handler.get_pending_tool_calls = AsyncMock(return_value=[])

        await self.session_handler.check_and_remove_pending_tool_call("call1")

        mock_warning.assert_called_once()
        self.assertIn("No pending tool calls found", mock_warning.call_args[0][0])
        # Should not attempt to update session state
        self.mock_session_manager.update_session_state.assert_not_called()


if __name__ == "__main__":
    unittest.main()
