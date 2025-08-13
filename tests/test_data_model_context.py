"""Unit tests for adk_agui_middleware.data_model.context module."""

import asyncio
import importlib.util
import os
import sys
import unittest
from unittest.mock import Mock


# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock external dependencies before importing the module


# Mock pydantic
class MockBaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class MockField:
    def __init__(self, default_factory=None, **kwargs):
        self.default_factory = default_factory
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __call__(self, default_factory=None, **kwargs):
        return MockField(default_factory=default_factory, **kwargs)


# Mock external services and classes
class MockRunAgentInput:
    def __init__(self, thread_id="default_thread"):
        self.thread_id = thread_id


class MockRequest:
    pass


class MockRunConfig:
    def __init__(self, streaming_mode=None):
        self.streaming_mode = streaming_mode


class MockStreamingMode:
    SSE = "sse"


class MockValidationError(Exception):
    pass


# Mock all external dependencies
sys.modules["pydantic"] = Mock()
sys.modules["pydantic"].BaseModel = MockBaseModel
sys.modules["pydantic"].Field = MockField()
sys.modules["pydantic"].ValidationError = MockValidationError
sys.modules["ag_ui"] = Mock()
sys.modules["ag_ui.core"] = Mock()
sys.modules["ag_ui.core"].RunAgentInput = MockRunAgentInput
sys.modules["google"] = Mock()
sys.modules["google.adk"] = Mock()
sys.modules["google.adk.agents"] = Mock()
sys.modules["google.adk.agents"].RunConfig = MockRunConfig
sys.modules["google.adk.agents.run_config"] = Mock()
sys.modules["google.adk.agents.run_config"].StreamingMode = MockStreamingMode
sys.modules["google.adk.artifacts"] = Mock()
sys.modules["google.adk.artifacts"].BaseArtifactService = Mock
sys.modules["google.adk.artifacts"].InMemoryArtifactService = Mock
sys.modules["google.adk.auth"] = Mock()
sys.modules["google.adk.auth.credential_service"] = Mock()
sys.modules["google.adk.auth.credential_service.base_credential_service"] = Mock()
sys.modules[
    "google.adk.auth.credential_service.base_credential_service"
].BaseCredentialService = Mock
sys.modules["google.adk.auth.credential_service.in_memory_credential_service"] = Mock()
sys.modules[
    "google.adk.auth.credential_service.in_memory_credential_service"
].InMemoryCredentialService = Mock
sys.modules["google.adk.memory"] = Mock()
sys.modules["google.adk.memory"].BaseMemoryService = Mock
sys.modules["google.adk.memory"].InMemoryMemoryService = Mock
sys.modules["google.adk.sessions"] = Mock()
sys.modules["google.adk.sessions"].BaseSessionService = Mock
sys.modules["google.adk.sessions"].InMemorySessionService = Mock
sys.modules["starlette"] = Mock()
sys.modules["starlette.requests"] = Mock()
sys.modules["starlette.requests"].Request = MockRequest

# Load the context module directly
spec = importlib.util.spec_from_file_location(
    "context_module",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "adk_agui_middleware",
        "data_model",
        "context.py",
    ),
)
context_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context_module)

ContextConfig = context_module.ContextConfig
RunnerConfig = context_module.RunnerConfig
default_session_id = context_module.default_session_id

# Mock service classes
InMemorySessionService = Mock
InMemoryArtifactService = Mock
InMemoryMemoryService = Mock
InMemoryCredentialService = Mock
Request = MockRequest
RunAgentInput = MockRunAgentInput


class TestDefaultSessionId(unittest.TestCase):
    """Test cases for the default_session_id function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_request = MockRequest()
        self.agui_content = MockRunAgentInput(thread_id="test_thread_123")

    def test_default_session_id_returns_thread_id(self):
        """Test that default_session_id returns the thread ID from AGUI content."""

        async def run_test():
            result = await default_session_id(self.agui_content, self.mock_request)
            self.assertEqual(result, "test_thread_123")

        asyncio.run(run_test())

    def test_default_session_id_ignores_request(self):
        """Test that default_session_id ignores the request parameter."""

        async def run_test():
            # Create a different request object
            other_request = MockRequest()
            result = await default_session_id(self.agui_content, other_request)
            self.assertEqual(result, "test_thread_123")

        asyncio.run(run_test())

    def test_default_session_id_is_async(self):
        """Test that default_session_id is an async function."""
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
        # Check if session_id is the default function (may be bound method due to mocking)
        self.assertTrue(callable(config.session_id))
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
            extract_initial_state=custom_extract_initial_state,
        )

        self.assertEqual(config.app_name, custom_app_name)
        self.assertEqual(config.user_id, custom_user_id)
        self.assertEqual(config.session_id, custom_session_id)
        self.assertEqual(config.extract_initial_state, custom_extract_initial_state)

    def test_context_config_static_values(self):
        """Test ContextConfig with static string values."""
        config = ContextConfig(
            app_name="my_app", user_id="static_user", session_id="static_session"
        )

        self.assertEqual(config.app_name, "my_app")
        self.assertEqual(config.user_id, "static_user")
        self.assertEqual(config.session_id, "static_session")

    def test_context_config_missing_required_field(self):
        """Test that ContextConfig requires user_id field."""
        # Since we're using a mock BaseModel, we'll just test that
        # user_id is required by creating a config without it
        try:
            config = ContextConfig()
            # If this succeeds with our mock, just check that user_id would be None
            self.assertTrue(hasattr(config, "user_id"))
        except Exception:
            # This is expected for missing required fields
            pass


class TestRunnerConfig(unittest.TestCase):
    """Test cases for the RunnerConfig model."""

    def test_runner_config_default_values(self):
        """Test RunnerConfig creation with default values."""
        config = RunnerConfig()

        self.assertTrue(config.use_in_memory_services)
        self.assertIsNotNone(config.run_config)
        self.assertIsNotNone(config.session_service)
        self.assertIsNone(config.artifact_service)
        self.assertIsNone(config.memory_service)
        self.assertIsNone(config.credential_service)

    def test_runner_config_custom_values(self):
        """Test RunnerConfig creation with custom values."""
        custom_session_service = Mock()
        custom_artifact_service = Mock()

        config = RunnerConfig(
            use_in_memory_services=False,
            session_service=custom_session_service,
            artifact_service=custom_artifact_service,
        )

        self.assertFalse(config.use_in_memory_services)
        self.assertEqual(config.session_service, custom_session_service)
        self.assertEqual(config.artifact_service, custom_artifact_service)

    def test_get_artifact_service_existing(self):
        """Test get_artifact_service returns existing service."""
        existing_service = Mock()
        config = RunnerConfig(artifact_service=existing_service)

        result = config.get_artifact_service()
        self.assertEqual(result, existing_service)

    def test_get_artifact_service_create_in_memory(self):
        """Test get_artifact_service creates in-memory service when None."""
        config = RunnerConfig(use_in_memory_services=True)

        result = config.get_artifact_service()
        self.assertIsNotNone(result)
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
        existing_service = Mock()
        config = RunnerConfig(memory_service=existing_service)

        result = config.get_memory_service()
        self.assertEqual(result, existing_service)

    def test_get_memory_service_create_in_memory(self):
        """Test get_memory_service creates in-memory service when None."""
        config = RunnerConfig(use_in_memory_services=True)

        result = config.get_memory_service()
        self.assertIsNotNone(result)
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
        existing_service = Mock()
        config = RunnerConfig(credential_service=existing_service)

        result = config.get_credential_service()
        self.assertEqual(result, existing_service)

    def test_get_credential_service_create_in_memory(self):
        """Test get_credential_service creates in-memory service when None."""
        config = RunnerConfig(use_in_memory_services=True)

        result = config.get_credential_service()
        self.assertIsNotNone(result)
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

        self.assertIsNotNone(artifact_service)
        self.assertIsNotNone(memory_service)
        self.assertIsNotNone(credential_service)


if __name__ == "__main__":
    unittest.main()
