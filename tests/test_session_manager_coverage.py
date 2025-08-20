"""Additional tests for session.py manager to boost coverage."""

from unittest.mock import AsyncMock, Mock

import pytest
from google.adk.events import Event
from google.adk.sessions import BaseSessionService, Session

from adk_agui_middleware.data_model.session import SessionParameter
from adk_agui_middleware.manager.session import SessionManager

from test_utils import BaseTestCase


class TestSessionManagerCoverage(BaseTestCase):
    """Additional tests for SessionManager to improve coverage."""

    def setUp(self):
        super().setUp()
        self.mock_service = Mock(spec=BaseSessionService)
        self.manager = SessionManager(self.mock_service)
        self.session_param = SessionParameter(
            app_name="test_app", user_id="test_user", session_id="test_session"
        )

    @pytest.mark.asyncio
    async def test_get_session_success(self):
        """Test successful session retrieval."""
        mock_session = Mock(spec=Session)
        self.mock_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.manager.get_session(self.session_param)

        assert result == mock_session
        self.mock_service.get_session.assert_called_once_with(
            session_id="test_session", app_name="test_app", user_id="test_user"
        )

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """Test session retrieval when session not found."""
        self.mock_service.get_session = AsyncMock(return_value=None)

        result = await self.manager.get_session(self.session_param)

        assert result is None

    @pytest.mark.asyncio
    async def test_check_and_create_session_exists(self):
        """Test check and create when session already exists."""
        mock_session = Mock(spec=Session)
        self.mock_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.manager.check_and_create_session(self.session_param)

        assert result == mock_session
        # Should not call create_session
        assert not self.mock_service.create_session.called

    @pytest.mark.asyncio
    async def test_check_and_create_session_create_new(self):
        """Test check and create when session doesn't exist."""
        # First call returns None (not found), second call would be create
        self.mock_service.get_session = AsyncMock(return_value=None)

        mock_new_session = Mock(spec=Session)
        self.mock_service.create_session = AsyncMock(return_value=mock_new_session)

        result = await self.manager.check_and_create_session(self.session_param)

        assert result == mock_new_session
        self.mock_service.create_session.assert_called_once_with(
            session_id="test_session",
            user_id="test_user",
            app_name="test_app",
            state={},
        )

    @pytest.mark.asyncio
    async def test_check_and_create_session_with_initial_state(self):
        """Test check and create with initial state."""
        self.mock_service.get_session = AsyncMock(return_value=None)

        mock_new_session = Mock(spec=Session)
        self.mock_service.create_session = AsyncMock(return_value=mock_new_session)

        initial_state = {"key1": "value1", "initialized": True}

        result = await self.manager.check_and_create_session(
            self.session_param, initial_state
        )

        assert result == mock_new_session
        self.mock_service.create_session.assert_called_once_with(
            session_id="test_session",
            user_id="test_user",
            app_name="test_app",
            state=initial_state,
        )

    @pytest.mark.asyncio
    async def test_update_session_state_success(self):
        """Test successful session state update."""
        mock_session = Mock(spec=Session)
        self.mock_service.get_session = AsyncMock(return_value=mock_session)
        self.mock_service.append_event = AsyncMock()

        state_updates = {"key1": "new_value", "key2": "added_value"}

        result = await self.manager.update_session_state(
            self.session_param, state_updates
        )

        assert result is True

        # Verify append_event was called with correct parameters
        self.mock_service.append_event.assert_called_once()
        call_args = self.mock_service.append_event.call_args
        assert call_args[0][0] == mock_session  # First arg is session

        # Check the event structure
        event = call_args[0][1]
        assert isinstance(event, Event)
        assert event.author == "system"
        assert event.actions.state_delta == state_updates

    @pytest.mark.asyncio
    async def test_update_session_state_session_not_found(self):
        """Test state update when session not found."""
        self.mock_service.get_session = AsyncMock(return_value=None)

        with patch(
            "adk_agui_middleware.manager.session.record_warning_log"
        ) as mock_log:
            result = await self.manager.update_session_state(
                self.session_param, {"key": "value"}
            )

            assert result is False
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_session_state_no_updates(self):
        """Test state update with no updates provided."""
        mock_session = Mock(spec=Session)
        self.mock_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.manager.update_session_state(self.session_param, None)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_session_state_empty_updates(self):
        """Test state update with empty updates."""
        mock_session = Mock(spec=Session)
        self.mock_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.manager.update_session_state(self.session_param, {})

        assert result is False

    @pytest.mark.asyncio
    async def test_get_session_state_success(self):
        """Test successful session state retrieval."""
        mock_session = Mock(spec=Session)
        mock_session.state = {"key1": "value1", "key2": "value2"}
        self.mock_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.manager.get_session_state(self.session_param)

        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.asyncio
    async def test_get_session_state_session_not_found(self):
        """Test session state retrieval when session not found."""
        self.mock_service.get_session = AsyncMock(return_value=None)

        with patch(
            "adk_agui_middleware.manager.session.record_warning_log"
        ) as mock_log:
            result = await self.manager.get_session_state(self.session_param)

            assert result == {}
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_state_exception(self):
        """Test session state retrieval with exception."""
        self.mock_service.get_session = AsyncMock(
            side_effect=Exception("Database error")
        )

        with patch("adk_agui_middleware.manager.session.record_error_log") as mock_log:
            result = await self.manager.get_session_state(self.session_param)

            assert result == {}
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_value_success(self):
        """Test successful state value retrieval."""
        mock_session = Mock(spec=Session)
        mock_session.state = {"key1": "value1", "key2": "value2"}
        self.mock_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.manager.get_state_value(self.session_param, "key1")

        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_state_value_key_not_found(self):
        """Test state value retrieval when key not found."""
        mock_session = Mock(spec=Session)
        mock_session.state = {"key1": "value1"}
        self.mock_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.manager.get_state_value(
            self.session_param, "nonexistent_key", "default_value"
        )

        assert result == "default_value"

    @pytest.mark.asyncio
    async def test_get_state_value_session_not_found(self):
        """Test state value retrieval when session not found."""
        self.mock_service.get_session = AsyncMock(return_value=None)

        with patch(
            "adk_agui_middleware.manager.session.record_warning_log"
        ) as mock_log:
            result = await self.manager.get_state_value(
                self.session_param, "key1", "default"
            )

            assert result == "default"
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_value_exception(self):
        """Test state value retrieval with exception."""
        self.mock_service.get_session = AsyncMock(
            side_effect=RuntimeError("Service error")
        )

        with patch("adk_agui_middleware.manager.session.record_error_log") as mock_log:
            result = await self.manager.get_state_value(
                self.session_param, "key1", "fallback"
            )

            assert result == "fallback"
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_value_no_default(self):
        """Test state value retrieval without default value."""
        mock_session = Mock(spec=Session)
        mock_session.state = {}
        self.mock_service.get_session = AsyncMock(return_value=mock_session)

        result = await self.manager.get_state_value(self.session_param, "missing_key")

        assert result is None

    def test_session_manager_initialization(self):
        """Test SessionManager proper initialization."""
        service = Mock(spec=BaseSessionService)
        manager = SessionManager(service)

        assert manager.session_service == service

    @pytest.mark.asyncio
    async def test_event_creation_in_update(self):
        """Test proper event creation during state update."""

        mock_session = Mock(spec=Session)
        self.mock_service.get_session = AsyncMock(return_value=mock_session)
        self.mock_service.append_event = AsyncMock()

        state_updates = {"test_key": "test_value"}

        with patch("time.time", return_value=1234567890.0):
            await self.manager.update_session_state(self.session_param, state_updates)

        # Verify event structure
        call_args = self.mock_service.append_event.call_args
        event = call_args[0][1]

        assert event.author == "system"
        assert "state_update_" in event.invocation_id
        assert event.actions.state_delta == state_updates
        assert event.timestamp == 1234567890.0

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent session operations."""
        import asyncio

        mock_session = Mock(spec=Session)
        mock_session.state = {"counter": 0}
        self.mock_service.get_session = AsyncMock(return_value=mock_session)
        self.mock_service.append_event = AsyncMock()

        # Simulate concurrent state updates
        tasks = []
        for i in range(5):
            task = self.manager.update_session_state(
                self.session_param, {f"key_{i}": f"value_{i}"}
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)
        assert self.mock_service.append_event.call_count == 5
