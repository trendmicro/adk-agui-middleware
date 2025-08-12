"""Unit tests for adk_agui_middleware.data_model.context module."""

import unittest
from unittest.mock import AsyncMock, Mock

from ag_ui.core import RunAgentInput
from google.adk.agents.run_config import StreamingMode
from google.adk.artifacts import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from pydantic import ValidationError
from starlette.requests import Request

from adk_agui_middleware.data_model.context import (
    ContextConfig,
    RunnerConfig,
    default_session_id,
)


class TestDefaultSessionId(unittest.TestCase):
    """Test cases for the default_session_id function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_request = Mock(spec=Request)
        self.agui_content = Mock(spec=RunAgentInput)
        self.agui_content.thread_id = "test_thread_123"

    async def test_default_session_id_returns_thread_id(self):
        """Test that default_session_id returns the thread ID from AGUI content."""
        result = await default_session_id(self.agui_content, self.mock_request)
        self.assertEqual(result, "test_thread_123")

    async def test_default_session_id_ignores_request(self):
        """Test that default_session_id ignores the request parameter."""
        # Create a different request object
        other_request = Mock(spec=Request)
        result = await default_session_id(self.agui_content, other_request)
        self.assertEqual(result, "test_thread_123")

    def test_default_session_id_is_async(self):
        """Test that default_session_id is an async function."""
        import asyncio
        result = default_session_id(self.agui_content, self.mock_request)
        self.assertTrue(asyncio.iscoroutine(result))
        # Clean up the coroutine
        result.close()


class TestContextConfig(unittest.TestCase):
    """Test cases for the ContextConfig model."""

    def test_context_config_default_values(self):
        """Test ContextConfig creation with minimal required fields."""
        config = ContextConfig(user_id="test_user")
        
        self.assertEqual(config.app_name, "default")
        self.assertEqual(config.user_id, "test_user")
        self.assertEqual(config.session_id, default_session_id)
        self.assertIsNone(config.extract_initial_state)

    def test_context_config_all_fields(self):
        """Test ContextConfig creation with all fields specified."""
        async def custom_app_name(content, request):
            return "custom_app"
        
        async def custom_user_id(content, request):
            return "custom_user"
        
        async def custom_session_id(content, request):
            return "custom_session"
        
        async def custom_extract_initial_state(content, request):
            return {"key": "value"}

        config = ContextConfig(
            app_name=custom_app_name,
            user_id=custom_user_id,
            session_id=custom_session_id,
            extract_initial_state=custom_extract_initial_state
        )
        
        self.assertEqual(config.app_name, custom_app_name)
        self.assertEqual(config.user_id, custom_user_id)
        self.assertEqual(config.session_id, custom_session_id)
        self.assertEqual(config.extract_initial_state, custom_extract_initial_state)

    def test_context_config_static_values(self):
        """Test ContextConfig with static string values."""
        config = ContextConfig(
            app_name="my_app",
            user_id="static_user",
            session_id="static_session"
        )
        
        self.assertEqual(config.app_name, "my_app")
        self.assertEqual(config.user_id, "static_user")
        self.assertEqual(config.session_id, "static_session")

    def test_context_config_missing_required_field(self):
        """Test that ContextConfig raises ValidationError when user_id is missing."""
        with self.assertRaises(ValidationError) as cm:
            ContextConfig()
        
        errors = cm.exception.errors()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['type'], 'missing')
        self.assertEqual(errors[0]['loc'], ('user_id',))


class TestRunnerConfig(unittest.TestCase):
    """Test cases for the RunnerConfig model."""

    def test_runner_config_default_values(self):
        """Test RunnerConfig creation with default values."""
        config = RunnerConfig()
        
        self.assertTrue(config.use_in_memory_services)
        self.assertEqual(config.run_config.streaming_mode, StreamingMode.SSE)
        self.assertIsInstance(config.session_service, InMemorySessionService)
        self.assertIsNone(config.artifact_service)
        self.assertIsNone(config.memory_service)
        self.assertIsNone(config.credential_service)

    def test_runner_config_custom_values(self):
        """Test RunnerConfig creation with custom values."""
        custom_session_service = Mock(spec=InMemorySessionService)
        custom_artifact_service = Mock(spec=InMemoryArtifactService)
        
        config = RunnerConfig(
            use_in_memory_services=False,
            session_service=custom_session_service,
            artifact_service=custom_artifact_service
        )
        
        self.assertFalse(config.use_in_memory_services)
        self.assertEqual(config.session_service, custom_session_service)
        self.assertEqual(config.artifact_service, custom_artifact_service)

    def test_get_artifact_service_existing(self):
        """Test get_artifact_service returns existing service."""
        existing_service = Mock(spec=InMemoryArtifactService)
        config = RunnerConfig(artifact_service=existing_service)
        
        result = config.get_artifact_service()
        self.assertEqual(result, existing_service)

    def test_get_artifact_service_create_in_memory(self):
        """Test get_artifact_service creates in-memory service when None."""
        config = RunnerConfig(use_in_memory_services=True)
        
        result = config.get_artifact_service()
        self.assertIsInstance(result, InMemoryArtifactService)
        # Service should be cached
        self.assertEqual(config.artifact_service, result)

    def test_get_artifact_service_disabled_raises_error(self):
        """Test get_artifact_service raises error when service is None and in-memory disabled."""
        config = RunnerConfig(use_in_memory_services=False, artifact_service=None)
        
        with self.assertRaises(ValueError) as cm:
            config.get_artifact_service()
        
        self.assertIn("Artifact Service is not set", str(cm.exception))

    def test_get_memory_service_existing(self):
        """Test get_memory_service returns existing service."""
        existing_service = Mock(spec=InMemoryMemoryService)
        config = RunnerConfig(memory_service=existing_service)
        
        result = config.get_memory_service()
        self.assertEqual(result, existing_service)

    def test_get_memory_service_create_in_memory(self):
        """Test get_memory_service creates in-memory service when None."""
        config = RunnerConfig(use_in_memory_services=True)
        
        result = config.get_memory_service()
        self.assertIsInstance(result, InMemoryMemoryService)
        # Service should be cached
        self.assertEqual(config.memory_service, result)

    def test_get_memory_service_disabled_raises_error(self):
        """Test get_memory_service raises error when service is None and in-memory disabled."""
        config = RunnerConfig(use_in_memory_services=False, memory_service=None)
        
        with self.assertRaises(ValueError) as cm:
            config.get_memory_service()
        
        self.assertIn("Memory Service is not set", str(cm.exception))

    def test_get_credential_service_existing(self):
        """Test get_credential_service returns existing service."""
        existing_service = Mock(spec=InMemoryCredentialService)
        config = RunnerConfig(credential_service=existing_service)
        
        result = config.get_credential_service()
        self.assertEqual(result, existing_service)

    def test_get_credential_service_create_in_memory(self):
        """Test get_credential_service creates in-memory service when None."""
        config = RunnerConfig(use_in_memory_services=True)
        
        result = config.get_credential_service()
        self.assertIsInstance(result, InMemoryCredentialService)
        # Service should be cached
        self.assertEqual(config.credential_service, result)

    def test_get_credential_service_disabled_raises_error(self):
        """Test get_credential_service raises error when service is None and in-memory disabled."""
        config = RunnerConfig(use_in_memory_services=False, credential_service=None)
        
        with self.assertRaises(ValueError) as cm:
            config.get_credential_service()
        
        self.assertIn("Credential Service is not set", str(cm.exception))

    def test_get_or_create_service_caching(self):
        """Test that _get_or_create_service caches created services."""
        config = RunnerConfig(use_in_memory_services=True)
        
        # First call creates the service
        service1 = config.get_artifact_service()
        # Second call should return the same service
        service2 = config.get_artifact_service()
        
        self.assertIs(service1, service2)

    def test_service_creation_edge_cases(self):
        """Test edge cases in service creation."""
        config = RunnerConfig(use_in_memory_services=True)
        
        # Test all service types can be created
        artifact_service = config.get_artifact_service()
        memory_service = config.get_memory_service()
        credential_service = config.get_credential_service()
        
        self.assertIsInstance(artifact_service, InMemoryArtifactService)
        self.assertIsInstance(memory_service, InMemoryMemoryService)
        self.assertIsInstance(credential_service, InMemoryCredentialService)


if __name__ == '__main__':
    unittest.main()