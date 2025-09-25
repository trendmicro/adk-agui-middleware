# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Comprehensive unit tests for adk_agui_middleware.manager.session module.

This test suite provides extensive coverage for the SessionManager class,
including error scenarios, edge cases, and integration with ADK session service.
"""

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from google.adk.events import Event, EventActions
from google.adk.sessions import BaseSessionService, Session

from adk_agui_middleware.data_model.session import SessionParameter
from adk_agui_middleware.manager.session import SessionManager


class TestSessionManager:
    """Comprehensive tests for SessionManager class."""

    @pytest.fixture
    def mock_session_service(self) -> Mock:
        """Create a mock session service."""
        service = Mock(spec=BaseSessionService)
        service.list_sessions = AsyncMock()
        service.get_session = AsyncMock()
        service.create_session = AsyncMock()
        service.delete_session = AsyncMock()
        service.append_event = AsyncMock()
        return service

    @pytest.fixture
    def session_manager(self, mock_session_service: Mock) -> SessionManager:
        """Create a SessionManager with mock session service."""
        return SessionManager(mock_session_service)

    @pytest.fixture
    def session_parameter(self) -> SessionParameter:
        """Create a test session parameter."""
        return SessionParameter(
            app_name="test_app",
            user_id="test_user_123",
            session_id="session_456"
        )

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock session object."""
        session = Mock(spec=Session)
        session.id = "session_456"
        session.user_id = "test_user_123"
        session.app_name = "test_app"
        session.state = {"key1": "value1", "key2": 42}
        return session

    # ========== Constructor Tests ==========

    def test_init(self, mock_session_service: Mock):
        """Test SessionManager initialization."""
        manager = SessionManager(mock_session_service)
        assert manager.session_service == mock_session_service

    # ========== List Sessions Tests ==========

    @pytest.mark.asyncio
    async def test_list_sessions_success(self, session_manager: SessionManager, mock_session_service: Mock):
        """Test successful listing of sessions."""
        mock_sessions = [Mock(spec=Session), Mock(spec=Session)]
        mock_response = Mock()
        mock_response.sessions = mock_sessions
        mock_session_service.list_sessions.return_value = mock_response

        result = await session_manager.list_sessions("test_app", "user_123")

        assert result == mock_sessions
        mock_session_service.list_sessions.assert_called_once_with(
            app_name="test_app", user_id="user_123"
        )

    @pytest.mark.asyncio
    async def test_list_sessions_empty_result(self, session_manager: SessionManager, mock_session_service: Mock):
        """Test listing sessions with empty result."""
        mock_response = Mock()
        mock_response.sessions = []
        mock_session_service.list_sessions.return_value = mock_response

        result = await session_manager.list_sessions("test_app", "user_123")

        assert result == []

    @pytest.mark.asyncio
    async def test_list_sessions_service_exception(self, session_manager: SessionManager, mock_session_service: Mock):
        """Test list sessions when service raises exception."""
        mock_session_service.list_sessions.side_effect = Exception("Service error")

        with pytest.raises(Exception, match="Service error"):
            await session_manager.list_sessions("test_app", "user_123")

    # ========== Get Session Tests ==========

    @pytest.mark.asyncio
    async def test_get_session_found(self, session_manager: SessionManager, mock_session_service: Mock,
                                   session_parameter: SessionParameter, mock_session: Mock):
        """Test successfully getting an existing session."""
        mock_session_service.get_session.return_value = mock_session

        result = await session_manager.get_session(session_parameter)

        assert result == mock_session
        mock_session_service.get_session.assert_called_once_with(
            session_id="session_456",
            app_name="test_app",
            user_id="test_user_123"
        )

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_manager: SessionManager, mock_session_service: Mock,
                                       session_parameter: SessionParameter):
        """Test getting a session that doesn't exist."""
        mock_session_service.get_session.return_value = None

        result = await session_manager.get_session(session_parameter)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_service_exception(self, session_manager: SessionManager, mock_session_service: Mock,
                                                session_parameter: SessionParameter):
        """Test get session when service raises exception."""
        mock_session_service.get_session.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await session_manager.get_session(session_parameter)

    # ========== Check and Create Session Tests ==========

    @pytest.mark.asyncio
    async def test_check_and_create_session_existing(self, session_manager: SessionManager,
                                                   mock_session_service: Mock, session_parameter: SessionParameter,
                                                   mock_session: Mock):
        """Test check_and_create_session when session already exists."""
        mock_session_service.get_session.return_value = mock_session

        result = await session_manager.check_and_create_session(session_parameter)

        assert result == mock_session
        mock_session_service.get_session.assert_called_once()
        mock_session_service.create_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_and_create_session_new_without_initial_state(self, session_manager: SessionManager,
                                                                    mock_session_service: Mock,
                                                                    session_parameter: SessionParameter,
                                                                    mock_session: Mock):
        """Test creating new session without initial state."""
        mock_session_service.get_session.return_value = None
        mock_session_service.create_session.return_value = mock_session

        result = await session_manager.check_and_create_session(session_parameter)

        assert result == mock_session
        mock_session_service.create_session.assert_called_once_with(
            session_id="session_456",
            user_id="test_user_123",
            app_name="test_app",
            state={}
        )

    @pytest.mark.asyncio
    async def test_check_and_create_session_new_with_initial_state(self, session_manager: SessionManager,
                                                                 mock_session_service: Mock,
                                                                 session_parameter: SessionParameter,
                                                                 mock_session: Mock):
        """Test creating new session with initial state."""
        initial_state = {"init_key": "init_value", "count": 0}
        mock_session_service.get_session.return_value = None
        mock_session_service.create_session.return_value = mock_session

        result = await session_manager.check_and_create_session(session_parameter, initial_state)

        assert result == mock_session
        mock_session_service.create_session.assert_called_once_with(
            session_id="session_456",
            user_id="test_user_123",
            app_name="test_app",
            state=initial_state
        )

    @pytest.mark.asyncio
    async def test_check_and_create_session_create_failure(self, session_manager: SessionManager,
                                                          mock_session_service: Mock,
                                                          session_parameter: SessionParameter):
        """Test session creation failure."""
        mock_session_service.get_session.return_value = None
        mock_session_service.create_session.side_effect = Exception("Creation failed")

        with pytest.raises(Exception, match="Creation failed"):
            await session_manager.check_and_create_session(session_parameter)

    # ========== Delete Session Tests ==========

    @pytest.mark.asyncio
    async def test_delete_session_success(self, session_manager: SessionManager, mock_session_service: Mock,
                                        session_parameter: SessionParameter):
        """Test successful session deletion."""
        await session_manager.delete_session(session_parameter)

        mock_session_service.delete_session.assert_called_once_with(
            session_id="session_456",
            app_name="test_app",
            user_id="test_user_123"
        )

    @pytest.mark.asyncio
    async def test_delete_session_service_exception(self, session_manager: SessionManager,
                                                   mock_session_service: Mock, session_parameter: SessionParameter):
        """Test delete session when service raises exception."""
        mock_session_service.delete_session.side_effect = Exception("Deletion failed")

        with pytest.raises(Exception, match="Deletion failed"):
            await session_manager.delete_session(session_parameter)

    # ========== Update Session State Tests ==========

    @pytest.mark.asyncio
    async def test_update_session_state_success(self, session_manager: SessionManager, mock_session_service: Mock,
                                              session_parameter: SessionParameter, mock_session: Mock):
        """Test successful session state update."""
        state_updates = {"new_key": "new_value", "counter": 1}
        mock_session_service.get_session.return_value = mock_session

        with patch('time.time', return_value=1234567890.0):
            result = await session_manager.update_session_state(session_parameter, state_updates)

        assert result is True
        mock_session_service.append_event.assert_called_once()

        # Verify the event that was appended
        call_args = mock_session_service.append_event.call_args
        session_arg, event_arg = call_args[0]

        assert session_arg == mock_session
        assert isinstance(event_arg, Event)
        assert event_arg.author == "system"
        assert event_arg.actions.state_delta == state_updates
        assert "state_update_" in event_arg.invocation_id

    @pytest.mark.asyncio
    async def test_update_session_state_session_not_found(self, session_manager: SessionManager,
                                                         mock_session_service: Mock, session_parameter: SessionParameter):
        """Test state update when session doesn't exist."""
        state_updates = {"key": "value"}
        mock_session_service.get_session.return_value = None

        with patch('adk_agui_middleware.manager.session.record_warning_log') as mock_log:
            result = await session_manager.update_session_state(session_parameter, state_updates)

        assert result is False
        mock_log.assert_called_once()
        mock_session_service.append_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_session_state_no_updates(self, session_manager: SessionManager, mock_session_service: Mock,
                                                  session_parameter: SessionParameter, mock_session: Mock):
        """Test state update with no updates provided."""
        mock_session_service.get_session.return_value = mock_session

        with patch('adk_agui_middleware.manager.session.record_warning_log') as mock_log:
            result = await session_manager.update_session_state(session_parameter, None)

        assert result is False
        mock_log.assert_called_once()
        mock_session_service.append_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_session_state_empty_updates(self, session_manager: SessionManager, mock_session_service: Mock,
                                                     session_parameter: SessionParameter, mock_session: Mock):
        """Test state update with empty updates dictionary."""
        mock_session_service.get_session.return_value = mock_session

        with patch('adk_agui_middleware.manager.session.record_warning_log') as mock_log:
            result = await session_manager.update_session_state(session_parameter, {})

        assert result is False
        mock_log.assert_called_once()
        mock_session_service.append_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_session_state_append_event_failure(self, session_manager: SessionManager,
                                                           mock_session_service: Mock, session_parameter: SessionParameter,
                                                           mock_session: Mock):
        """Test state update when append_event fails."""
        state_updates = {"key": "value"}
        mock_session_service.get_session.return_value = mock_session
        mock_session_service.append_event.side_effect = Exception("Append failed")

        with pytest.raises(Exception, match="Append failed"):
            await session_manager.update_session_state(session_parameter, state_updates)

    # ========== Get Session State Tests ==========

    @pytest.mark.asyncio
    async def test_get_session_state_success(self, session_manager: SessionManager, mock_session_service: Mock,
                                           session_parameter: SessionParameter, mock_session: Mock):
        """Test successfully getting session state."""
        expected_state = {"key1": "value1", "key2": 42}
        mock_session.state = expected_state
        mock_session_service.get_session.return_value = mock_session

        result = await session_manager.get_session_state(session_parameter)

        assert result == expected_state

    @pytest.mark.asyncio
    async def test_get_session_state_session_not_found(self, session_manager: SessionManager,
                                                      mock_session_service: Mock, session_parameter: SessionParameter):
        """Test getting state when session doesn't exist."""
        mock_session_service.get_session.return_value = None

        with patch('adk_agui_middleware.manager.session.record_warning_log') as mock_log:
            result = await session_manager.get_session_state(session_parameter)

        assert result == {}
        mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_state_exception_handling(self, session_manager: SessionManager,
                                                       mock_session_service: Mock, session_parameter: SessionParameter):
        """Test exception handling in get_session_state."""
        mock_session_service.get_session.side_effect = Exception("Database error")

        with patch('adk_agui_middleware.manager.session.record_error_log') as mock_log:
            result = await session_manager.get_session_state(session_parameter)

        assert result == {}
        mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_state_empty_state(self, session_manager: SessionManager, mock_session_service: Mock,
                                                session_parameter: SessionParameter, mock_session: Mock):
        """Test getting empty session state."""
        mock_session.state = {}
        mock_session_service.get_session.return_value = mock_session

        result = await session_manager.get_session_state(session_parameter)

        assert result == {}

    # ========== Get State Value Tests ==========

    @pytest.mark.asyncio
    async def test_get_state_value_success(self, session_manager: SessionManager, mock_session_service: Mock,
                                         session_parameter: SessionParameter, mock_session: Mock):
        """Test successfully getting a specific state value."""
        mock_session.state = {"key1": "value1", "key2": 42, "nested": {"inner": "data"}}
        mock_session_service.get_session.return_value = mock_session

        result1 = await session_manager.get_state_value(session_parameter, "key1")
        result2 = await session_manager.get_state_value(session_parameter, "key2")
        result3 = await session_manager.get_state_value(session_parameter, "nested")

        assert result1 == "value1"
        assert result2 == 42
        assert result3 == {"inner": "data"}

    @pytest.mark.asyncio
    async def test_get_state_value_key_not_found_with_default(self, session_manager: SessionManager,
                                                            mock_session_service: Mock, session_parameter: SessionParameter,
                                                            mock_session: Mock):
        """Test getting state value for non-existent key with default."""
        mock_session.state = {"existing_key": "value"}
        mock_session_service.get_session.return_value = mock_session

        result = await session_manager.get_state_value(session_parameter, "non_existent", "default_value")

        assert result == "default_value"

    @pytest.mark.asyncio
    async def test_get_state_value_key_not_found_no_default(self, session_manager: SessionManager,
                                                          mock_session_service: Mock, session_parameter: SessionParameter,
                                                          mock_session: Mock):
        """Test getting state value for non-existent key without default."""
        mock_session.state = {"existing_key": "value"}
        mock_session_service.get_session.return_value = mock_session

        result = await session_manager.get_state_value(session_parameter, "non_existent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_state_value_session_not_found(self, session_manager: SessionManager, mock_session_service: Mock,
                                                    session_parameter: SessionParameter):
        """Test getting state value when session doesn't exist."""
        mock_session_service.get_session.return_value = None

        with patch('adk_agui_middleware.manager.session.record_warning_log') as mock_log:
            result = await session_manager.get_state_value(session_parameter, "any_key", "default")

        assert result == "default"
        mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_value_exception_handling(self, session_manager: SessionManager, mock_session_service: Mock,
                                                     session_parameter: SessionParameter):
        """Test exception handling in get_state_value."""
        mock_session_service.get_session.side_effect = Exception("Service error")

        with patch('adk_agui_middleware.manager.session.record_error_log') as mock_log:
            result = await session_manager.get_state_value(session_parameter, "key", "default")

        assert result == "default"
        mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_value_various_types(self, session_manager: SessionManager, mock_session_service: Mock,
                                                session_parameter: SessionParameter, mock_session: Mock):
        """Test getting state values of various types."""
        mock_session.state = {
            "string": "text",
            "integer": 123,
            "float": 45.67,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "none": None
        }
        mock_session_service.get_session.return_value = mock_session

        string_val = await session_manager.get_state_value(session_parameter, "string")
        int_val = await session_manager.get_state_value(session_parameter, "integer")
        float_val = await session_manager.get_state_value(session_parameter, "float")
        bool_val = await session_manager.get_state_value(session_parameter, "boolean")
        list_val = await session_manager.get_state_value(session_parameter, "list")
        dict_val = await session_manager.get_state_value(session_parameter, "dict")
        none_val = await session_manager.get_state_value(session_parameter, "none")

        assert string_val == "text"
        assert int_val == 123
        assert float_val == 45.67
        assert bool_val is True
        assert list_val == [1, 2, 3]
        assert dict_val == {"nested": "value"}
        assert none_val is None

    # ========== Integration Tests ==========

    @pytest.mark.asyncio
    async def test_session_lifecycle_integration(self, session_manager: SessionManager, mock_session_service: Mock):
        """Test complete session lifecycle: create, update, get, delete."""
        session_param = SessionParameter(
            app_name="integration_app",
            user_id="integration_user",
            session_id="integration_session"
        )

        mock_session = Mock(spec=Session)
        mock_session.state = {}

        # Initially no session exists
        mock_session_service.get_session.return_value = None
        # Session creation
        mock_session_service.create_session.return_value = mock_session

        # 1. Check and create session
        created_session = await session_manager.check_and_create_session(session_param, {"init": "data"})
        assert created_session == mock_session

        # 2. Update state
        mock_session_service.get_session.return_value = mock_session
        mock_session.state = {"init": "data", "updated": "value"}

        update_result = await session_manager.update_session_state(session_param, {"updated": "value"})
        assert update_result is True

        # 3. Get state
        state = await session_manager.get_session_state(session_param)
        assert "init" in state
        assert "updated" in state

        # 4. Get specific value
        value = await session_manager.get_state_value(session_param, "updated")
        assert value == "value"

        # 5. Delete session
        await session_manager.delete_session(session_param)
        mock_session_service.delete_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_operations_same_session(self, session_manager: SessionManager, mock_session_service: Mock,
                                                     session_parameter: SessionParameter, mock_session: Mock):
        """Test handling concurrent operations on the same session."""
        mock_session_service.get_session.return_value = mock_session

        # Simulate concurrent state updates
        update_tasks = [
            session_manager.update_session_state(session_parameter, {"key1": "value1"}),
            session_manager.update_session_state(session_parameter, {"key2": "value2"}),
            session_manager.update_session_state(session_parameter, {"key3": "value3"})
        ]

        results = await asyncio.gather(*update_tasks, return_exceptions=True)

        # All operations should succeed
        assert all(result is True for result in results)
        # append_event should be called for each update
        assert mock_session_service.append_event.call_count == 3

    @pytest.mark.asyncio
    async def test_edge_case_special_characters_in_state(self, session_manager: SessionManager,
                                                       mock_session_service: Mock, session_parameter: SessionParameter,
                                                       mock_session: Mock):
        """Test handling state with special characters and edge case values."""
        special_state = {
            "unicode": "测试中文字符🔥",
            "empty_string": "",
            "large_number": 999999999999999999,
            "negative": -123.456,
            "special_chars": "!@#$%^&*()",
            "json_like": '{"nested": "json"}',
            "boolean_strings": "true",
            "none_string": "null"
        }

        mock_session.state = special_state
        mock_session_service.get_session.return_value = mock_session

        # Test getting the complete state
        result = await session_manager.get_session_state(session_parameter)
        assert result == special_state

        # Test getting individual values
        unicode_val = await session_manager.get_state_value(session_parameter, "unicode")
        empty_val = await session_manager.get_state_value(session_parameter, "empty_string")
        large_num = await session_manager.get_state_value(session_parameter, "large_number")

        assert unicode_val == "测试中文字符🔥"
        assert empty_val == ""
        assert large_num == 999999999999999999