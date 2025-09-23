# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.manager.session module."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from google.adk.events import Event, EventActions
from google.adk.sessions import BaseSessionService, Session

from adk_agui_middleware.data_model.session import SessionParameter
from adk_agui_middleware.manager.session import SessionManager


class TestSessionManager(unittest.TestCase):
    """Test cases for the SessionManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session_service = Mock(spec=BaseSessionService)
        self.session_manager = SessionManager(self.mock_session_service)
        self.session_parameter = SessionParameter(
            app_name="test_app", user_id="test_user", session_id="test_session"
        )

    def test_init(self):
        """Test SessionManager initialization."""
        self.assertEqual(
            self.session_manager.session_service, self.mock_session_service
        )

    async def test_get_session_success(self):
        """Test get_session returns session successfully."""
        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.session_manager.get_session(self.session_parameter)

        self.assertEqual(result, mock_session)
        self.mock_session_service.get_session.assert_called_once_with(
            session_id="test_session", app_name="test_app", user_id="test_user"
        )

    async def test_get_session_not_found(self):
        """Test get_session returns None when session not found."""
        self.mock_session_service.get_session = AsyncMock(return_value=None)

        result = await self.session_manager.get_session(self.session_parameter)

        self.assertIsNone(result)

    async def test_check_and_create_session_existing(self):
        """Test check_and_create_session returns existing session."""
        existing_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=existing_session)

        result = await self.session_manager.check_and_create_session(
            self.session_parameter
        )

        self.assertEqual(result, existing_session)
        # Should not call create_session if session exists
        self.mock_session_service.create_session.assert_not_called()

    async def test_check_and_create_session_new_without_initial_state(self):
        """Test check_and_create_session creates new session without initial state."""
        new_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=None)
        self.mock_session_service.create_session = AsyncMock(return_value=new_session)

        result = await self.session_manager.check_and_create_session(
            self.session_parameter
        )

        self.assertEqual(result, new_session)
        self.mock_session_service.create_session.assert_called_once_with(
            session_id="test_session",
            user_id="test_user",
            app_name="test_app",
            state={},
        )

    async def test_check_and_create_session_new_with_initial_state(self):
        """Test check_and_create_session creates new session with initial state."""
        new_session = Mock(spec=Session)
        initial_state = {"key1": "value1", "key2": "value2"}

        self.mock_session_service.get_session = AsyncMock(return_value=None)
        self.mock_session_service.create_session = AsyncMock(return_value=new_session)

        result = await self.session_manager.check_and_create_session(
            self.session_parameter, initial_state
        )

        self.assertEqual(result, new_session)
        self.mock_session_service.create_session.assert_called_once_with(
            session_id="test_session",
            user_id="test_user",
            app_name="test_app",
            state=initial_state,
        )

    @patch("adk_agui_middleware.manager.session.record_warning_log")
    async def test_update_session_state_session_not_found(self, mock_warning_log):
        """Test update_session_state returns False when session not found."""
        self.mock_session_service.get_session = AsyncMock(return_value=None)
        state_updates = {"key": "value"}

        result = await self.session_manager.update_session_state(
            self.session_parameter, state_updates
        )

        self.assertFalse(result)
        mock_warning_log.assert_called_once()
        self.assertIn("Session not found", mock_warning_log.call_args[0][0])

    @patch("adk_agui_middleware.manager.session.record_warning_log")
    async def test_update_session_state_no_updates(self, mock_warning_log):
        """Test update_session_state returns False when no state updates provided."""
        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.session_manager.update_session_state(
            self.session_parameter, None
        )

        self.assertFalse(result)
        mock_warning_log.assert_called_once()

    @patch("adk_agui_middleware.manager.session.record_warning_log")
    async def test_update_session_state_empty_updates(self, mock_warning_log):
        """Test update_session_state returns False when empty state updates."""
        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.session_manager.update_session_state(
            self.session_parameter, {}
        )

        self.assertFalse(result)
        mock_warning_log.assert_called_once()

    @patch("time.time")
    async def test_update_session_state_success(self, mock_time):
        """Test update_session_state successfully updates session state."""
        mock_time.return_value = 1234567890.5
        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        self.mock_session_service.append_event = AsyncMock()

        state_updates = {"key1": "value1", "key2": 42}

        result = await self.session_manager.update_session_state(
            self.session_parameter, state_updates
        )

        self.assertTrue(result)

        # Verify event was created correctly
        self.mock_session_service.append_event.assert_called_once()
        call_args = self.mock_session_service.append_event.call_args

        session_arg = call_args[0][0]
        event_arg = call_args[0][1]

        self.assertEqual(session_arg, mock_session)
        self.assertIsInstance(event_arg, Event)
        self.assertEqual(event_arg.author, "system")
        self.assertEqual(event_arg.actions.state_delta, state_updates)
        self.assertEqual(event_arg.timestamp, 1234567890.5)
        self.assertIn("state_update_", event_arg.invocation_id)

    async def test_get_session_state_success(self):
        """Test get_session_state returns session state successfully."""
        mock_session = Mock(spec=Session)
        mock_session.state = {"key1": "value1", "key2": "value2"}
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.session_manager.get_session_state(self.session_parameter)

        expected = {"key1": "value1", "key2": "value2"}
        self.assertEqual(result, expected)

    @patch("adk_agui_middleware.manager.session.record_warning_log")
    async def test_get_session_state_session_not_found(self, mock_warning_log):
        """Test get_session_state returns empty dict when session not found."""
        self.mock_session_service.get_session = AsyncMock(return_value=None)

        result = await self.session_manager.get_session_state(self.session_parameter)

        self.assertEqual(result, {})
        mock_warning_log.assert_called_once()

    @patch("adk_agui_middleware.manager.session.record_error_log")
    async def test_get_session_state_exception(self, mock_error_log):
        """Test get_session_state handles exceptions gracefully."""
        self.mock_session_service.get_session = AsyncMock(
            side_effect=Exception("Database error")
        )

        result = await self.session_manager.get_session_state(self.session_parameter)

        self.assertEqual(result, {})
        mock_error_log.assert_called_once()
        self.assertIn("Failed to get session state", mock_error_log.call_args[0][0])

    async def test_get_state_value_success(self):
        """Test get_state_value returns specific value from session state."""
        mock_session = Mock(spec=Session)
        mock_session.state = {"key1": "value1", "key2": 42, "key3": None}
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.session_manager.get_state_value(
            self.session_parameter, "key2"
        )

        self.assertEqual(result, 42)

    async def test_get_state_value_with_default(self):
        """Test get_state_value returns default when key not found."""
        mock_session = Mock(spec=Session)
        mock_session.state = {"key1": "value1"}
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.session_manager.get_state_value(
            self.session_parameter, "nonexistent_key", "default_value"
        )

        self.assertEqual(result, "default_value")

    async def test_get_state_value_none_default(self):
        """Test get_state_value returns None when key not found and no default."""
        mock_session = Mock(spec=Session)
        mock_session.state = {"key1": "value1"}
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.session_manager.get_state_value(
            self.session_parameter, "nonexistent_key"
        )

        self.assertIsNone(result)

    @patch("adk_agui_middleware.manager.session.record_warning_log")
    async def test_get_state_value_session_not_found(self, mock_warning_log):
        """Test get_state_value returns default when session not found."""
        self.mock_session_service.get_session = AsyncMock(return_value=None)

        result = await self.session_manager.get_state_value(
            self.session_parameter, "key", "fallback"
        )

        self.assertEqual(result, "fallback")
        mock_warning_log.assert_called_once()

    @patch("adk_agui_middleware.manager.session.record_error_log")
    async def test_get_state_value_exception(self, mock_error_log):
        """Test get_state_value handles exceptions gracefully."""
        self.mock_session_service.get_session = AsyncMock(
            side_effect=Exception("Connection error")
        )

        result = await self.session_manager.get_state_value(
            self.session_parameter, "key", "error_fallback"
        )

        self.assertEqual(result, "error_fallback")
        mock_error_log.assert_called_once()

    async def test_session_parameter_usage_consistency(self):
        """Test that SessionParameter is used consistently across methods."""
        # Test that all methods use session parameter correctly
        self.mock_session_service.get_session = AsyncMock(return_value=None)
        self.mock_session_service.create_session = AsyncMock(return_value=Mock())

        # Create session parameter with specific values
        param = SessionParameter(
            app_name="specific_app",
            user_id="specific_user",
            session_id="specific_session",
        )

        # Call various methods
        await self.session_manager.get_session(param)
        await self.session_manager.check_and_create_session(param)
        await self.session_manager.get_session_state(param)
        await self.session_manager.get_state_value(param, "test_key")

        # Verify all calls used the same parameter values
        for call in self.mock_session_service.get_session.call_args_list:
            kwargs = call.kwargs
            self.assertEqual(kwargs["app_name"], "specific_app")
            self.assertEqual(kwargs["user_id"], "specific_user")
            self.assertEqual(kwargs["session_id"], "specific_session")

    async def test_complex_state_updates(self):
        """Test update_session_state with complex data types."""
        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        self.mock_session_service.append_event = AsyncMock()

        complex_state = {
            "list_data": [1, 2, 3],
            "dict_data": {"nested": {"deep": "value"}},
            "null_data": None,
            "boolean_data": True,
            "number_data": 42.5,
        }

        result = await self.session_manager.update_session_state(
            self.session_parameter, complex_state
        )

        self.assertTrue(result)

        # Verify complex data was passed correctly
        call_args = self.mock_session_service.append_event.call_args
        event_arg = call_args[0][1]
        self.assertEqual(event_arg.actions.state_delta, complex_state)

    @patch("time.time")
    async def test_event_creation_uniqueness(self, mock_time):
        """Test that each update creates unique event IDs."""
        mock_time.side_effect = [1234567890, 1234567891]  # Different timestamps

        mock_session = Mock(spec=Session)
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)
        self.mock_session_service.append_event = AsyncMock()

        # Perform two updates
        await self.session_manager.update_session_state(
            self.session_parameter, {"update1": "value1"}
        )
        await self.session_manager.update_session_state(
            self.session_parameter, {"update2": "value2"}
        )

        # Verify two different events were created
        self.assertEqual(self.mock_session_service.append_event.call_count, 2)

        call1 = self.mock_session_service.append_event.call_args_list[0][0][1]
        call2 = self.mock_session_service.append_event.call_args_list[1][0][1]

        # Events should have different IDs and timestamps
        self.assertNotEqual(call1.invocation_id, call2.invocation_id)
        self.assertNotEqual(call1.timestamp, call2.timestamp)

    async def test_concurrent_operations(self):
        """Test that manager handles concurrent operations correctly."""
        import asyncio

        mock_session = Mock(spec=Session)
        mock_session.state = {"counter": 0}
        self.mock_session_service.get_session = AsyncMock(return_value=mock_session)

        # Simulate concurrent state reads
        tasks = [
            self.session_manager.get_session_state(self.session_parameter)
            for _ in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should return the same state
        for result in results:
            self.assertEqual(result, {"counter": 0})

        # Verify get_session was called for each operation
        self.assertEqual(self.mock_session_service.get_session.call_count, 5)

    def test_event_actions_creation(self):
        """Test that EventActions are created correctly."""
        state_delta = {"test_key": "test_value"}

        # Create event actions as done in the actual method
        actions = EventActions(state_delta=state_delta)

        self.assertEqual(actions.state_delta, state_delta)


if __name__ == "__main__":
    unittest.main()
