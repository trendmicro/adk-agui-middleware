"""Unit tests for adk_agui_middleware.handler.session module."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from google.adk.sessions import Session

from adk_agui_middleware.data_model.session import SessionParameter
from adk_agui_middleware.handler.session import SessionHandler


class TestSessionHandler(unittest.TestCase):
    """Test cases for the SessionHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session_manager = Mock()
        self.session_parameter = SessionParameter(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session"
        )
        self.handler = SessionHandler(
            session_manger=self.mock_session_manager,
            session_parameter=self.session_parameter
        )

    def test_init(self):
        """Test SessionHandler initialization."""
        self.assertEqual(self.handler.session_manger, self.mock_session_manager)
        self.assertEqual(self.handler.session_parameter, self.session_parameter)

    def test_app_name_property(self):
        """Test app_name property returns correct value."""
        self.assertEqual(self.handler.app_name, "test_app")

    def test_user_id_property(self):
        """Test user_id property returns correct value."""
        self.assertEqual(self.handler.user_id, "test_user")

    def test_session_id_property(self):
        """Test session_id property returns correct value."""
        self.assertEqual(self.handler.session_id, "test_session")

    def test_get_pending_tool_calls_dict(self):
        """Test get_pending_tool_calls_dict static method."""
        pending_calls = ["tool1", "tool2", "tool3"]
        result = SessionHandler.get_pending_tool_calls_dict(pending_calls)
        
        expected = {"pending_tool_calls": pending_calls}
        self.assertEqual(result, expected)

    def test_get_pending_tool_calls_dict_empty_list(self):
        """Test get_pending_tool_calls_dict with empty list."""
        result = SessionHandler.get_pending_tool_calls_dict([])
        
        expected = {"pending_tool_calls": []}
        self.assertEqual(result, expected)

    async def test_get_session(self):
        """Test get_session method."""
        mock_session = Mock(spec=Session)
        self.mock_session_manager.get_session = AsyncMock(return_value=mock_session)
        
        result = await self.handler.get_session()
        
        self.assertEqual(result, mock_session)
        self.mock_session_manager.get_session.assert_called_once_with(self.session_parameter)

    async def test_get_session_none(self):
        """Test get_session method returning None."""
        self.mock_session_manager.get_session = AsyncMock(return_value=None)
        
        result = await self.handler.get_session()
        
        self.assertIsNone(result)

    async def test_get_session_state(self):
        """Test get_session_state method."""
        expected_state = {"key1": "value1", "pending_tool_calls": ["tool1"]}
        self.mock_session_manager.get_session_state = AsyncMock(return_value=expected_state)
        
        result = await self.handler.get_session_state()
        
        self.assertEqual(result, expected_state)
        self.mock_session_manager.get_session_state.assert_called_once_with(self.session_parameter)

    async def test_check_and_create_session_with_initial_state(self):
        """Test check_and_create_session with initial state."""
        mock_session = Mock(spec=Session)
        initial_state = {"initial_key": "initial_value"}
        self.mock_session_manager.check_and_create_session = AsyncMock(return_value=mock_session)
        
        result = await self.handler.check_and_create_session(initial_state)
        
        self.assertEqual(result, mock_session)
        self.mock_session_manager.check_and_create_session.assert_called_once_with(
            session_parameter=self.session_parameter,
            initial_state=initial_state
        )

    async def test_check_and_create_session_without_initial_state(self):
        """Test check_and_create_session without initial state."""
        mock_session = Mock(spec=Session)
        self.mock_session_manager.check_and_create_session = AsyncMock(return_value=mock_session)
        
        result = await self.handler.check_and_create_session()
        
        self.assertEqual(result, mock_session)
        self.mock_session_manager.check_and_create_session.assert_called_once_with(
            session_parameter=self.session_parameter,
            initial_state=None
        )

    async def test_update_session_state_success(self):
        """Test update_session_state successful update."""
        state_updates = {"key": "value", "count": 42}
        self.mock_session_manager.update_session_state = AsyncMock(return_value=True)
        
        result = await self.handler.update_session_state(state_updates)
        
        self.assertTrue(result)
        self.mock_session_manager.update_session_state.assert_called_once_with(
            session_parameter=self.session_parameter,
            state_updates=state_updates
        )

    async def test_update_session_state_failure(self):
        """Test update_session_state failed update."""
        state_updates = {"key": "value"}
        self.mock_session_manager.update_session_state = AsyncMock(return_value=False)
        
        result = await self.handler.update_session_state(state_updates)
        
        self.assertFalse(result)

    @patch('adk_agui_middleware.handler.session.record_warning_log')
    @patch('adk_agui_middleware.handler.session.record_log')
    async def test_check_and_remove_pending_tool_call_success(self, mock_log, mock_warning_log):
        """Test successful removal of pending tool call."""
        tool_call_id = "tool123"
        pending_calls = ["tool123", "tool456"]
        
        # Mock the methods
        self.handler.get_pending_tool_calls = AsyncMock(return_value=pending_calls)
        self.mock_session_manager.update_session_state = AsyncMock(return_value=True)
        
        await self.handler.check_and_remove_pending_tool_call(tool_call_id)
        
        # Verify tool was removed from list
        expected_updated_calls = ["tool456"]
        
        # Check that update_session_state was called correctly
        self.mock_session_manager.update_session_state.assert_called_once()
        call_args = self.mock_session_manager.update_session_state.call_args
        self.assertEqual(call_args[1]['session_parameter'], self.session_parameter)
        self.assertEqual(call_args[1]['state_updates']['pending_tool_calls'], expected_updated_calls)
        
        # Verify logging
        mock_log.assert_called()
        mock_warning_log.assert_not_called()

    @patch('adk_agui_middleware.handler.session.record_warning_log')
    async def test_check_and_remove_pending_tool_call_not_found(self, mock_warning_log):
        """Test removal of non-existent pending tool call."""
        tool_call_id = "nonexistent_tool"
        pending_calls = ["tool123", "tool456"]
        
        self.handler.get_pending_tool_calls = AsyncMock(return_value=pending_calls)
        
        await self.handler.check_and_remove_pending_tool_call(tool_call_id)
        
        # Should not call update_session_state
        self.mock_session_manager.update_session_state.assert_not_called()
        
        # Should log warning
        mock_warning_log.assert_called_once()
        self.assertIn("No pending tool calls found", mock_warning_log.call_args[0][0])

    @patch('adk_agui_middleware.handler.session.record_error_log')
    @patch('adk_agui_middleware.handler.session.record_log')
    async def test_add_pending_tool_call_success(self, mock_log, mock_error_log):
        """Test successful addition of pending tool call."""
        tool_call_id = "new_tool"
        existing_pending_calls = ["tool123"]
        
        # Mock session state retrieval
        session_state = {"pending_tool_calls": existing_pending_calls}
        self.mock_session_manager.get_session_state = AsyncMock(return_value=session_state)
        self.mock_session_manager.update_session_state = AsyncMock(return_value=True)
        
        await self.handler.add_pending_tool_call(tool_call_id)
        
        # Verify state was updated with new tool call
        expected_updated_calls = ["tool123", "new_tool"]
        
        self.mock_session_manager.update_session_state.assert_called_once()
        call_args = self.mock_session_manager.update_session_state.call_args
        self.assertEqual(call_args[0][1]['pending_tool_calls'], expected_updated_calls)
        
        # Verify logging
        self.assertEqual(mock_log.call_count, 2)  # Initial log + success log
        mock_error_log.assert_not_called()

    @patch('adk_agui_middleware.handler.session.record_error_log')
    @patch('adk_agui_middleware.handler.session.record_log')
    async def test_add_pending_tool_call_already_exists(self, mock_log, mock_error_log):
        """Test adding tool call that already exists in pending list."""
        tool_call_id = "existing_tool"
        existing_pending_calls = ["existing_tool", "tool123"]
        
        session_state = {"pending_tool_calls": existing_pending_calls}
        self.mock_session_manager.get_session_state = AsyncMock(return_value=session_state)
        
        await self.handler.add_pending_tool_call(tool_call_id)
        
        # Should not update state since tool call already exists
        self.mock_session_manager.update_session_state.assert_not_called()
        
        # Should still log the initial attempt
        mock_log.assert_called_once()
        mock_error_log.assert_not_called()

    @patch('adk_agui_middleware.handler.session.record_error_log')
    @patch('adk_agui_middleware.handler.session.record_log')
    async def test_add_pending_tool_call_empty_initial_state(self, mock_log, mock_error_log):
        """Test adding tool call when no pending_tool_calls exist yet."""
        tool_call_id = "first_tool"
        
        # Mock session state without pending_tool_calls key
        session_state = {"other_key": "other_value"}
        self.mock_session_manager.get_session_state = AsyncMock(return_value=session_state)
        self.mock_session_manager.update_session_state = AsyncMock(return_value=True)
        
        await self.handler.add_pending_tool_call(tool_call_id)
        
        # Verify state was updated with new tool call list
        expected_updated_calls = ["first_tool"]
        
        self.mock_session_manager.update_session_state.assert_called_once()
        call_args = self.mock_session_manager.update_session_state.call_args
        self.assertEqual(call_args[0][1]['pending_tool_calls'], expected_updated_calls)

    @patch('adk_agui_middleware.handler.session.record_error_log')
    @patch('adk_agui_middleware.handler.session.record_log')
    async def test_add_pending_tool_call_exception(self, mock_log, mock_error_log):
        """Test handling exception during add_pending_tool_call."""
        tool_call_id = "error_tool"
        
        # Mock exception during get_session_state
        self.mock_session_manager.get_session_state = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        await self.handler.add_pending_tool_call(tool_call_id)
        
        # Should log error
        mock_error_log.assert_called_once()
        error_message = mock_error_log.call_args[0][0]
        self.assertIn("Failed to add pending tool call", error_message)

    @patch('adk_agui_middleware.handler.session.record_warning_log')
    @patch('adk_agui_middleware.handler.session.record_error_log')
    async def test_get_pending_tool_calls_success(self, mock_error_log, mock_warning_log):
        """Test successful retrieval of pending tool calls."""
        expected_calls = ["tool1", "tool2"]
        session_state = {
            "test_session": {"pending_tool_calls": expected_calls}
        }
        self.mock_session_manager.get_session_state = AsyncMock(return_value=session_state)
        
        result = await self.handler.get_pending_tool_calls()
        
        self.assertEqual(result, expected_calls)
        mock_error_log.assert_not_called()
        mock_warning_log.assert_not_called()

    @patch('adk_agui_middleware.handler.session.record_warning_log')
    @patch('adk_agui_middleware.handler.session.record_error_log')
    async def test_get_pending_tool_calls_no_session(self, mock_error_log, mock_warning_log):
        """Test get_pending_tool_calls when session doesn't exist."""
        session_state = {"other_session": {"data": "value"}}
        self.mock_session_manager.get_session_state = AsyncMock(return_value=session_state)
        
        result = await self.handler.get_pending_tool_calls()
        
        self.assertIsNone(result)
        mock_warning_log.assert_called_once()
        self.assertIn("Session test_session not found", mock_warning_log.call_args[0][0])
        mock_error_log.assert_not_called()

    @patch('adk_agui_middleware.handler.session.record_warning_log')
    @patch('adk_agui_middleware.handler.session.record_error_log')
    async def test_get_pending_tool_calls_no_pending_calls_key(self, mock_error_log, mock_warning_log):
        """Test get_pending_tool_calls when pending_tool_calls key missing."""
        session_state = {
            "test_session": {"other_data": "value"}
        }
        self.mock_session_manager.get_session_state = AsyncMock(return_value=session_state)
        
        result = await self.handler.get_pending_tool_calls()
        
        self.assertEqual(result, [])  # Should return empty list as default
        mock_error_log.assert_not_called()
        mock_warning_log.assert_not_called()

    @patch('adk_agui_middleware.handler.session.record_warning_log')
    @patch('adk_agui_middleware.handler.session.record_error_log')
    async def test_get_pending_tool_calls_exception(self, mock_error_log, mock_warning_log):
        """Test handling exception during get_pending_tool_calls."""
        self.mock_session_manager.get_session_state = AsyncMock(
            side_effect=Exception("Network error")
        )
        
        result = await self.handler.get_pending_tool_calls()
        
        self.assertIsNone(result)
        mock_error_log.assert_called_once()
        error_message = mock_error_log.call_args[0][0]
        self.assertIn("Failed to check pending tool calls", error_message)
        mock_warning_log.assert_not_called()

    def test_session_parameter_modification(self):
        """Test that modifying session parameter affects handler properties."""
        # Create handler with different session parameter
        new_param = SessionParameter(
            app_name="new_app",
            user_id="new_user", 
            session_id="new_session"
        )
        new_handler = SessionHandler(self.mock_session_manager, new_param)
        
        self.assertEqual(new_handler.app_name, "new_app")
        self.assertEqual(new_handler.user_id, "new_user")
        self.assertEqual(new_handler.session_id, "new_session")

    async def test_async_method_call_order(self):
        """Test that async methods can be called in sequence."""
        # Setup mocks
        self.mock_session_manager.get_session = AsyncMock(return_value=Mock())
        self.mock_session_manager.get_session_state = AsyncMock(return_value={})
        self.mock_session_manager.check_and_create_session = AsyncMock(return_value=Mock())
        self.mock_session_manager.update_session_state = AsyncMock(return_value=True)
        
        # Call methods in sequence
        session = await self.handler.get_session()
        state = await self.handler.get_session_state()
        created_session = await self.handler.check_and_create_session()
        update_result = await self.handler.update_session_state({"key": "value"})
        
        # Verify all methods were called
        self.assertIsNotNone(session)
        self.assertEqual(state, {})
        self.assertIsNotNone(created_session)
        self.assertTrue(update_result)


if __name__ == '__main__':
    unittest.main()