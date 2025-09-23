# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Additional unit tests for adk_agui_middleware.manager.session module to increase coverage."""

import unittest
from unittest.mock import AsyncMock, Mock, patch
import time

from google.adk.events import Event, EventActions
from google.adk.sessions import BaseSessionService, Session

from adk_agui_middleware.data_model.session import SessionParameter
from adk_agui_middleware.manager.session import SessionManager


class TestSessionManagerAdditional(unittest.TestCase):
    """Additional test cases for SessionManager class to increase coverage."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session_service = Mock(spec=BaseSessionService)
        self.manager = SessionManager(self.mock_session_service)
        self.session_parameter = SessionParameter(
            session_id="test-session",
            app_name="test-app",
            user_id="test-user"
        )

    async def test_get_session_success(self):
        """Test successful session retrieval."""
        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        
        result = await self.manager.get_session(self.session_parameter)
        
        self.assertEqual(result, mock_session)
        self.mock_session_service.get_session.assert_called_once_with(
            session_id="test-session",
            app_name="test-app",
            user_id="test-user"
        )

    async def test_get_session_not_found(self):
        """Test session retrieval when session not found."""
        self.mock_session_service.get_session = AsyncMock(return_value=None)
        
        result = await self.manager.get_session(self.session_parameter)
        
        self.assertIsNone(result)

    async def test_check_and_create_session_existing(self):
        """Test check_and_create_session when session exists."""
        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        
        result = await self.manager.check_and_create_session(self.session_parameter)
        
        self.assertEqual(result, mock_session)
        self.mock_session_service.create_session.assert_not_called()

    async def test_check_and_create_session_new_without_initial_state(self):
        """Test check_and_create_session when creating new session without initial state."""
        self.mock_session_service.get_session = AsyncMock(return_value=None)
        mock_new_session = Mock(spec=Session)
        self.mock_session_service.create_session = AsyncMock(return_value=mock_new_session)
        
        result = await self.manager.check_and_create_session(self.session_parameter)
        
        self.assertEqual(result, mock_new_session)
        self.mock_session_service.create_session.assert_called_once_with(
            session_id="test-session",
            user_id="test-user",
            app_name="test-app",
            state={}
        )

    async def test_check_and_create_session_new_with_initial_state(self):
        """Test check_and_create_session when creating new session with initial state."""
        self.mock_session_service.get_session = AsyncMock(return_value=None)
        mock_new_session = Mock(spec=Session)
        self.mock_session_service.create_session = AsyncMock(return_value=mock_new_session)
        
        initial_state = {"key": "value"}
        result = await self.manager.check_and_create_session(
            self.session_parameter, initial_state
        )
        
        self.assertEqual(result, mock_new_session)
        self.mock_session_service.create_session.assert_called_once_with(
            session_id="test-session",
            user_id="test-user",
            app_name="test-app",
            state=initial_state
        )

    @patch("adk_agui_middleware.manager.session.record_warning_log")
    async def test_update_session_state_session_not_found(self, mock_warning_log):
        """Test update_session_state when session not found."""
        self.mock_session_service.get_session = AsyncMock(return_value=None)
        
        result = await self.manager.update_session_state(
            self.session_parameter, {"key": "value"}
        )
        
        self.assertFalse(result)
        mock_warning_log.assert_called_once_with(
            "Session not found: test-app:test-session"
        )

    @patch("adk_agui_middleware.manager.session.record_warning_log")
    async def test_update_session_state_no_updates(self, mock_warning_log):
        """Test update_session_state when no state updates provided."""
        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        
        result = await self.manager.update_session_state(self.session_parameter, None)
        
        self.assertFalse(result)
        mock_warning_log.assert_called_once()

    @patch("adk_agui_middleware.manager.session.record_warning_log")
    async def test_update_session_state_empty_updates(self, mock_warning_log):
        """Test update_session_state when empty state updates provided."""
        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        
        result = await self.manager.update_session_state(self.session_parameter, {})
        
        self.assertFalse(result)
        mock_warning_log.assert_called_once()

    @patch("adk_agui_middleware.manager.session.time.time")
    async def test_update_session_state_success(self, mock_time):
        """Test successful session state update."""
        mock_time.return_value = 1234567890.0
        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        self.mock_session_service.append_event = AsyncMock()
        
        state_updates = {"key": "value", "count": 42}
        result = await self.manager.update_session_state(
            self.session_parameter, state_updates
        )
        
        self.assertTrue(result)
        
        # Verify the event was created correctly
        call_args = self.mock_session_service.append_event.call_args
        event = call_args[0][1]  # Second argument is the event
        
        self.assertIsInstance(event, Event)
        self.assertEqual(event.invocation_id, "state_update_1234567890")
        self.assertEqual(event.author, "system")
        self.assertEqual(event.actions.state_delta, state_updates)
        self.assertEqual(event.timestamp, 1234567890.0)

    async def test_get_session_state_success(self):
        """Test successful session state retrieval."""
        mock_session = Mock(spec=Session)
        mock_session.state = {"key1": "value1", "key2": "value2"}
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        
        result = await self.manager.get_session_state(self.session_parameter)
        
        self.assertEqual(result, {"key1": "value1", "key2": "value2"})

    @patch("adk_agui_middleware.manager.session.record_warning_log")
    async def test_get_session_state_session_not_found(self, mock_warning_log):
        """Test get_session_state when session not found."""
        self.mock_session_service.get_session = AsyncMock(return_value=None)
        
        result = await self.manager.get_session_state(self.session_parameter)
        
        self.assertEqual(result, {})
        mock_warning_log.assert_called_once_with(
            "Session not found: test-app:test-session"
        )

    @patch("adk_agui_middleware.manager.session.record_error_log")
    async def test_get_session_state_exception(self, mock_error_log):
        """Test get_session_state when exception occurs."""
        self.mock_session_service.get_session = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        result = await self.manager.get_session_state(self.session_parameter)
        
        self.assertEqual(result, {})
        mock_error_log.assert_called_once()

    async def test_get_state_value_success(self):
        """Test successful state value retrieval."""
        mock_session = Mock(spec=Session)
        mock_session.state = {"key1": "value1", "key2": "value2"}
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        
        result = await self.manager.get_state_value(
            self.session_parameter, "key1"
        )
        
        self.assertEqual(result, "value1")

    async def test_get_state_value_with_default(self):
        """Test state value retrieval with default value."""
        mock_session = Mock(spec=Session)
        mock_session.state = {"key1": "value1"}
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        
        result = await self.manager.get_state_value(
            self.session_parameter, "nonexistent_key", "default_value"
        )
        
        self.assertEqual(result, "default_value")

    @patch("adk_agui_middleware.manager.session.record_warning_log")
    async def test_get_state_value_session_not_found(self, mock_warning_log):
        """Test get_state_value when session not found."""
        self.mock_session_service.get_session = AsyncMock(return_value=None)
        
        result = await self.manager.get_state_value(
            self.session_parameter, "key", "default"
        )
        
        self.assertEqual(result, "default")
        mock_warning_log.assert_called_once_with(
            "Session not found: test-app:test-session"
        )

    @patch("adk_agui_middleware.manager.session.record_error_log")
    async def test_get_state_value_exception(self, mock_error_log):
        """Test get_state_value when exception occurs."""
        self.mock_session_service.get_session = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        result = await self.manager.get_state_value(
            self.session_parameter, "key", "default"
        )
        
        self.assertEqual(result, "default")
        mock_error_log.assert_called_once()


if __name__ == "__main__":
    unittest.main()