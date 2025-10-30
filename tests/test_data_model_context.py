# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.data_model.context module."""

from unittest.mock import Mock

import pytest
from ag_ui.core import RunAgentInput
from fastapi import Request
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode

from adk_agui_middleware.tools.default_config_context import default_session_id
from adk_agui_middleware.data_model.config import RunnerConfig
from adk_agui_middleware.data_model.context import ConfigContext


class TestDefaultSessionId:
    """Test cases for default_session_id function."""

    @pytest.mark.asyncio
    async def test_default_session_id(self):
        """Test that default_session_id returns the thread_id from AGUI content."""
        agui_content = RunAgentInput(
            thread_id="test_thread_123",
            run_id="test_run",
            state={},
            messages=[],
            tools=[],
            context=[],
            forwarded_props={}
        )
        request = Mock(spec=Request)

        result = await default_session_id(agui_content, request)

        assert result == "test_thread_123"

    @pytest.mark.asyncio
    async def test_default_session_id_different_thread(self):
        """Test default_session_id with different thread ID."""
        agui_content = RunAgentInput(
            thread_id="another_thread_456",
            run_id="test_run",
            state={},
            messages=[],
            tools=[],
            context=[],
            forwarded_props={}
        )
        request = Mock(spec=Request)

        result = await default_session_id(agui_content, request)

        assert result == "another_thread_456"


class TestConfigContext:
    """Test cases for ConfigContext class."""

    def test_context_config_creation_minimal(self):
        """Test ConfigContext creation with minimal required fields."""

        async def mock_user_id(content, request):
            return "test_user"

        config = ConfigContext(user_id=mock_user_id)

        assert config.app_name == "default"
        assert config.user_id == mock_user_id
        assert config.session_id == default_session_id
        assert config.extract_initial_state is None

    def test_context_config_creation_all_fields(self):
        """Test ConfigContext creation with all fields specified."""

        async def mock_app_name(content, request):
            return "custom_app"

        async def mock_user_id(content, request):
            return "custom_user"

        async def mock_session_id(content, request):
            return "custom_session"

        async def mock_initial_state(content, request):
            return {"key": "value"}

        config = ConfigContext(
            app_name=mock_app_name,
            user_id=mock_user_id,
            session_id=mock_session_id,
            extract_initial_state=mock_initial_state,
        )

        assert config.app_name == mock_app_name
        assert config.user_id == mock_user_id
        assert config.session_id == mock_session_id
        assert config.extract_initial_state == mock_initial_state

    def test_context_config_static_values(self):
        """Test ConfigContext with static string values."""
        config = ConfigContext(
            app_name="static_app",
            user_id="static_user",
            session_id="static_session",
        )

        assert config.app_name == "static_app"
        assert config.user_id == "static_user"
        assert config.session_id == "static_session"


class TestRunnerConfig:
    """Test cases for RunnerConfig class."""

    def test_runner_config_default_values(self):
        """Test RunnerConfig creation with default values."""
        config = RunnerConfig()

        assert config.use_in_memory_services is True
        assert isinstance(config.run_config, RunConfig)
        assert config.run_config.streaming_mode == StreamingMode.SSE
        assert config.session_service is not None
        assert config.artifact_service is None
        assert config.memory_service is None
        assert config.credential_service is None

    def test_runner_config_custom_values(self):
        """Test RunnerConfig creation with custom values."""
        from google.adk.sessions import InMemorySessionService

        custom_run_config = RunConfig(streaming_mode=StreamingMode.NONE)
        mock_session_service = InMemorySessionService()

        config = RunnerConfig(
            use_in_memory_services=False,
            run_config=custom_run_config,
            session_service=mock_session_service,
        )

        assert config.use_in_memory_services is False
        assert config.run_config == custom_run_config
        assert config.session_service == mock_session_service

    def test_get_artifact_service_in_memory_enabled(self):
        """Test get_artifact_service with in-memory services enabled."""
        config = RunnerConfig(use_in_memory_services=True)

        service = config.get_artifact_service()

        assert service is not None
        assert config.artifact_service == service

    def test_get_artifact_service_in_memory_disabled(self):
        """Test get_artifact_service with in-memory services disabled."""
        config = RunnerConfig(use_in_memory_services=False)

        with pytest.raises(ValueError) as exc_info:
            config.get_artifact_service()

        assert "Artifact Service is not set" in str(exc_info.value)

    def test_get_memory_service_in_memory_enabled(self):
        """Test get_memory_service with in-memory services enabled."""
        config = RunnerConfig(use_in_memory_services=True)

        service = config.get_memory_service()

        assert service is not None
        assert config.memory_service == service

    def test_get_memory_service_in_memory_disabled(self):
        """Test get_memory_service with in-memory services disabled."""
        config = RunnerConfig(use_in_memory_services=False)

        with pytest.raises(ValueError) as exc_info:
            config.get_memory_service()

        assert "Memory Service is not set" in str(exc_info.value)

    def test_get_credential_service_in_memory_enabled(self):
        """Test get_credential_service with in-memory services enabled."""
        config = RunnerConfig(use_in_memory_services=True)

        service = config.get_credential_service()

        assert service is not None
        assert config.credential_service == service

    def test_get_credential_service_in_memory_disabled(self):
        """Test get_credential_service with in-memory services disabled."""
        config = RunnerConfig(use_in_memory_services=False)

        with pytest.raises(ValueError) as exc_info:
            config.get_credential_service()

        assert "Credential Service is not set" in str(exc_info.value)

    def test_service_caching(self):
        """Test that services are cached after first creation."""
        config = RunnerConfig(use_in_memory_services=True)

        # Get services multiple times
        artifact1 = config.get_artifact_service()
        artifact2 = config.get_artifact_service()
        memory1 = config.get_memory_service()
        memory2 = config.get_memory_service()

        # Should be the same instances
        assert artifact1 is artifact2
        assert memory1 is memory2

    def test_existing_service_returned(self):
        """Test that existing services are returned without replacement."""
        from google.adk.artifacts import InMemoryArtifactService

        mock_artifact_service = InMemoryArtifactService()
        config = RunnerConfig(
            use_in_memory_services=True, artifact_service=mock_artifact_service
        )

        service = config.get_artifact_service()

        assert service is mock_artifact_service
