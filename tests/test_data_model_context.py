"""Unit tests for adk_agui_middleware.data_model.context module."""

import unittest
from unittest.mock import Mock, AsyncMock

from ag_ui.core import RunAgentInput
from fastapi import Request
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode

from adk_agui_middleware.data_model.context import (
    ContextConfig,
    RunnerConfig,
    default_session_id,
)


class TestDefaultSessionId(unittest.TestCase):
    """Test cases for default_session_id function."""

    async def test_default_session_id(self):
        """Test that default_session_id returns the thread_id from AGUI content."""
        agui_content = RunAgentInput(thread_id="test_thread_123")
        request = Mock(spec=Request)
        
        result = await default_session_id(agui_content, request)
        
        self.assertEqual(result, "test_thread_123")

    async def test_default_session_id_different_thread(self):
        """Test default_session_id with different thread ID."""
        agui_content = RunAgentInput(thread_id="another_thread_456")
        request = Mock(spec=Request)
        
        result = await default_session_id(agui_content, request)
        
        self.assertEqual(result, "another_thread_456")


class TestContextConfig(unittest.TestCase):
    """Test cases for ContextConfig class."""

    def test_context_config_creation_minimal(self):
        """Test ContextConfig creation with minimal required fields."""
        async def mock_user_id(content, request):
            return "test_user"
            
        config = ContextConfig(user_id=mock_user_id)
        
        self.assertEqual(config.app_name, "default")
        self.assertEqual(config.user_id, mock_user_id)
        self.assertEqual(config.session_id, default_session_id)
        self.assertIsNone(config.extract_initial_state)

    def test_context_config_creation_all_fields(self):
        """Test ContextConfig creation with all fields specified."""
        async def mock_app_name(content, request):
            return "custom_app"
            
        async def mock_user_id(content, request):
            return "custom_user"
            
        async def mock_session_id(content, request):
            return "custom_session"
            
        async def mock_initial_state(content, request):
            return {"key": "value"}
            
        config = ContextConfig(
            app_name=mock_app_name,
            user_id=mock_user_id,
            session_id=mock_session_id,
            extract_initial_state=mock_initial_state,
        )
        
        self.assertEqual(config.app_name, mock_app_name)
        self.assertEqual(config.user_id, mock_user_id)
        self.assertEqual(config.session_id, mock_session_id)
        self.assertEqual(config.extract_initial_state, mock_initial_state)

    def test_context_config_static_values(self):
        """Test ContextConfig with static string values."""
        config = ContextConfig(
            app_name="static_app",
            user_id="static_user",
            session_id="static_session",
        )
        
        self.assertEqual(config.app_name, "static_app")
        self.assertEqual(config.user_id, "static_user")
        self.assertEqual(config.session_id, "static_session")


class TestRunnerConfig(unittest.TestCase):
    """Test cases for RunnerConfig class."""

    def test_runner_config_default_values(self):
        """Test RunnerConfig creation with default values."""
        config = RunnerConfig()
        
        self.assertTrue(config.use_in_memory_services)
        self.assertIsInstance(config.run_config, RunConfig)
        self.assertEqual(config.run_config.streaming_mode, StreamingMode.SSE)
        self.assertIsNotNone(config.session_service)
        self.assertIsNone(config.artifact_service)
        self.assertIsNone(config.memory_service)
        self.assertIsNone(config.credential_service)

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
        
        self.assertFalse(config.use_in_memory_services)
        self.assertEqual(config.run_config, custom_run_config)
        self.assertEqual(config.session_service, mock_session_service)

    def test_get_artifact_service_in_memory_enabled(self):
        """Test get_artifact_service with in-memory services enabled."""
        config = RunnerConfig(use_in_memory_services=True)
        
        service = config.get_artifact_service()
        
        self.assertIsNotNone(service)
        self.assertEqual(config.artifact_service, service)

    def test_get_artifact_service_in_memory_disabled(self):
        """Test get_artifact_service with in-memory services disabled."""
        config = RunnerConfig(use_in_memory_services=False)
        
        with self.assertRaises(ValueError) as cm:
            config.get_artifact_service()
        
        self.assertIn("Artifact Service is not set", str(cm.exception))

    def test_get_memory_service_in_memory_enabled(self):
        """Test get_memory_service with in-memory services enabled."""
        config = RunnerConfig(use_in_memory_services=True)
        
        service = config.get_memory_service()
        
        self.assertIsNotNone(service)
        self.assertEqual(config.memory_service, service)

    def test_get_memory_service_in_memory_disabled(self):
        """Test get_memory_service with in-memory services disabled."""
        config = RunnerConfig(use_in_memory_services=False)
        
        with self.assertRaises(ValueError) as cm:
            config.get_memory_service()
        
        self.assertIn("Memory Service is not set", str(cm.exception))

    def test_get_credential_service_in_memory_enabled(self):
        """Test get_credential_service with in-memory services enabled."""
        config = RunnerConfig(use_in_memory_services=True)
        
        service = config.get_credential_service()
        
        self.assertIsNotNone(service)
        self.assertEqual(config.credential_service, service)

    def test_get_credential_service_in_memory_disabled(self):
        """Test get_credential_service with in-memory services disabled."""
        config = RunnerConfig(use_in_memory_services=False)
        
        with self.assertRaises(ValueError) as cm:
            config.get_credential_service()
        
        self.assertIn("Credential Service is not set", str(cm.exception))

    def test_service_caching(self):
        """Test that services are cached after first creation."""
        config = RunnerConfig(use_in_memory_services=True)
        
        # Get services multiple times
        artifact1 = config.get_artifact_service()
        artifact2 = config.get_artifact_service()
        memory1 = config.get_memory_service()
        memory2 = config.get_memory_service()
        
        # Should be the same instances
        self.assertIs(artifact1, artifact2)
        self.assertIs(memory1, memory2)

    def test_existing_service_returned(self):
        """Test that existing services are returned without replacement."""
        from google.adk.artifacts import InMemoryArtifactService
        mock_artifact_service = InMemoryArtifactService()
        config = RunnerConfig(
            use_in_memory_services=True,
            artifact_service=mock_artifact_service
        )
        
        service = config.get_artifact_service()
        
        self.assertIs(service, mock_artifact_service)


if __name__ == "__main__":
    unittest.main()