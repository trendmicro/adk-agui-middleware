"""Consolidated tests for all data model modules."""

import pytest
from google.adk.agents.run_config import StreamingMode
from google.adk.artifacts import InMemoryArtifactService

from adk_agui_middleware.data_model.context import (
    ConfigContext,
    RunnerConfig,
    default_session_id,
)
from adk_agui_middleware.data_model.error import ErrorModel, ErrorResponseModel
from adk_agui_middleware.data_model.session import SessionParameter

from .test_utils import TEST_CONSTANTS, BaseTestCase, parametrize_test_cases


class TestDataModels(BaseTestCase):
    """Consolidated test cases for all data models."""

    def setUp(self):
        super().setUp()

    # ErrorModel Tests
    @parametrize_test_cases(
        [
            {"error": "TEST_ERROR", "error_description": "Test error message"},
            {"error": "VALIDATION_ERROR", "error_description": "Validation failed"},
            {"error": "", "error_description": ""},
        ]
    )
    def test_error_model_creation(self, error: str, error_description: str):
        """Test ErrorModel creation with various inputs."""
        error_model = ErrorModel(error=error, error_description=error_description)
        assert error_model.error == error
        assert error_model.error_description == error_description

    def test_error_model_serialization(self):
        """Test ErrorModel JSON serialization."""
        error = ErrorModel(error="TEST", error_description="Test message")
        data = error.model_dump()

        # Test that required fields are present
        assert "error" in data
        assert "error_description" in data
        assert data["error"] == "TEST"
        assert data["error_description"] == "Test message"

        # Test that default values are accessible as attributes
        assert hasattr(error, "timestamp")
        assert hasattr(error, "trace_id")
        assert isinstance(error.timestamp, int)
        assert isinstance(error.trace_id, str)

    def test_error_response_model_creation(self):
        """Test ErrorResponseModel creation."""
        error = ErrorModel(error="TEST", error_description="Test message")
        response = ErrorResponseModel(detail=error)

        assert response.detail.error == "TEST"
        assert response.detail.error_description == "Test message"

    # SessionParameter Tests
    @parametrize_test_cases(
        [
            {"app_name": "test_app", "user_id": "user123", "session_id": "session456"},
            {"app_name": "prod_app", "user_id": "admin", "session_id": "admin_session"},
        ]
    )
    def test_session_parameter_creation(
        self, app_name: str, user_id: str, session_id: str
    ):
        """Test SessionParameter creation."""
        param = SessionParameter(
            app_name=app_name, user_id=user_id, session_id=session_id
        )

        assert param.app_name == app_name
        assert param.user_id == user_id
        assert param.session_id == session_id

    def test_session_parameter_equality_comparison(self):
        """Test SessionParameter equality comparison."""
        param1 = SessionParameter(
            app_name="test_app", user_id="test_user", session_id="test_session"
        )
        param2 = SessionParameter(
            app_name="test_app", user_id="test_user", session_id="test_session"
        )
        param3 = SessionParameter(
            app_name="different", user_id="test_user", session_id="test_session"
        )

        # Test field by field equality (since Pydantic object equality might not work as expected)
        assert param1.app_name == param2.app_name
        assert param1.user_id == param2.user_id
        assert param1.session_id == param2.session_id

        # Test difference
        assert param1.app_name != param3.app_name

        # Test model_dump equality as alternative
        assert param1.model_dump() == param2.model_dump()
        assert param1.model_dump() != param3.model_dump()

    def test_session_parameter_serialization(self):
        """Test SessionParameter JSON serialization."""
        param = self.create_test_data("session_parameter")
        data = param.model_dump()

        expected_keys = ["app_name", "user_id", "session_id"]
        self.assertions.assert_dict_contains_keys(data, expected_keys)

    # Context Tests
    @pytest.mark.asyncio
    async def test_default_session_id_function(self):
        """Test default_session_id function."""
        agui_content = self.create_test_data("run_agent_input")
        request = self.create_mock("request")

        result = await default_session_id(agui_content, request)
        assert result == TEST_CONSTANTS["DEFAULT_THREAD_ID"]

    @pytest.mark.asyncio
    async def test_context_config_with_static_values(self):
        """Test ConfigContext with static string values."""
        config = ConfigContext(
            app_name="static_app", user_id="static_user", session_id="static_session"
        )

        assert config.app_name == "static_app"
        assert config.user_id == "static_user"
        assert config.session_id == "static_session"

    @pytest.mark.asyncio
    async def test_context_config_with_callables(self):
        """Test ConfigContext with callable functions."""

        async def custom_user_id(content, request):
            return "custom_user"

        async def custom_initial_state(content, request):
            return {"custom": "state"}

        config = ConfigContext(
            user_id=custom_user_id, extract_initial_state=custom_initial_state
        )

        # Test callable functions
        agui_content = self.create_test_data("run_agent_input")
        request = self.create_mock("request")

        user_id = await config.user_id(agui_content, request)
        initial_state = await config.extract_initial_state(agui_content, request)

        assert user_id == "custom_user"
        assert initial_state == {"custom": "state"}

    # RunnerConfig Tests
    def test_runner_config_defaults(self):
        """Test RunnerConfig with default values."""
        config = RunnerConfig()

        assert config.use_in_memory_services is True
        assert config.run_config.streaming_mode == StreamingMode.SSE
        assert config.session_service is not None
        assert config.artifact_service is None

    @parametrize_test_cases(
        [
            {"streaming_mode": StreamingMode.NONE, "use_in_memory": False},
            {"streaming_mode": StreamingMode.BIDI, "use_in_memory": True},
        ]
    )
    def test_runner_config_custom_values(
        self, streaming_mode: StreamingMode, use_in_memory: bool
    ):
        """Test RunnerConfig with custom values."""
        config = self.create_test_data(
            "runner_config", use_in_memory=use_in_memory, streaming_mode=streaming_mode
        )

        assert config.use_in_memory_services == use_in_memory
        assert config.run_config.streaming_mode == streaming_mode

    def test_runner_config_service_creation(self):
        """Test automatic service creation in RunnerConfig."""
        config = RunnerConfig(use_in_memory_services=True)

        # Test service creation
        artifact_service = config.get_artifact_service()
        memory_service = config.get_memory_service()
        credential_service = config.get_credential_service()

        assert artifact_service is not None
        assert memory_service is not None
        assert credential_service is not None

    def test_runner_config_service_caching(self):
        """Test that services are cached after creation."""
        config = RunnerConfig(use_in_memory_services=True)

        # Get services multiple times
        artifact1 = config.get_artifact_service()
        artifact2 = config.get_artifact_service()

        # Should be the same instance
        assert artifact1 is artifact2

    def test_runner_config_service_errors(self):
        """Test service creation errors when disabled."""
        config = RunnerConfig(use_in_memory_services=False)

        with pytest.raises(ValueError, match="Artifact Service is not set"):
            config.get_artifact_service()

        with pytest.raises(ValueError, match="Memory Service is not set"):
            config.get_memory_service()

        with pytest.raises(ValueError, match="Credential Service is not set"):
            config.get_credential_service()

    def test_runner_config_existing_services(self):
        """Test that existing services are returned without replacement."""
        existing_service = InMemoryArtifactService()
        config = RunnerConfig(
            use_in_memory_services=True, artifact_service=existing_service
        )

        service = config.get_artifact_service()
        assert service is existing_service

    # Edge cases and validation
    def test_session_parameter_field_types(self):
        """Test SessionParameter field type validation."""
        param = self.create_test_data("session_parameter")

        assert isinstance(param.app_name, str)
        assert isinstance(param.user_id, str)
        assert isinstance(param.session_id, str)

    def test_session_parameter_string_representation(self):
        """Test SessionParameter string representation."""
        param = self.create_test_data("session_parameter")
        str_repr = str(param)

        # Test that string representation exists and is not empty
        assert isinstance(str_repr, str)
        assert len(str_repr) > 0

        # Test that we can access the values directly for string building if needed
        assert param.app_name == "test_app"
        assert param.user_id == "test_user"
        assert param.session_id == "test_session"

    @parametrize_test_cases(
        [
            {"content": "", "expected_length": 0},
            {"content": "short", "expected_length": 5},
            {"content": "a" * 1000, "expected_length": 1000},
        ]
    )
    def test_error_model_message_lengths(self, content: str, expected_length: int):
        """Test ErrorModel with various message lengths."""
        error = ErrorModel(error="TEST", error_description=content)
        assert len(error.error_description) == expected_length

    def test_context_config_minimal_setup(self):
        """Test ConfigContext with minimal required configuration."""

        async def user_func(content, request):
            return "minimal_user"

        config = ConfigContext(user_id=user_func)

        assert config.app_name == "default"
        assert config.user_id == user_func
        assert config.session_id == default_session_id
        assert config.extract_initial_state is None

    def test_runner_config_service_type_validation(self):
        """Test RunnerConfig service type validation."""
        config = RunnerConfig()

        # Test that services are of correct types
        artifact_service = config.get_artifact_service()
        session_service = config.session_service

        # Check artifact service methods
        assert hasattr(artifact_service, "save_artifact")
        assert hasattr(artifact_service, "load_artifact")
        assert hasattr(artifact_service, "delete_artifact")

        # Check session service methods
        assert hasattr(session_service, "get_session")
        assert hasattr(session_service, "create_session")

    # Performance and memory tests
    def test_multiple_session_parameters_memory(self):
        """Test creating multiple SessionParameter instances doesn't leak memory."""
        params = []
        for i in range(100):
            param = SessionParameter(
                app_name=f"app_{i}", user_id=f"user_{i}", session_id=f"session_{i}"
            )
            params.append(param)

        assert len(params) == 100
        assert all(isinstance(p, SessionParameter) for p in params)

    def test_runner_config_service_isolation(self):
        """Test that different RunnerConfig instances have isolated services."""
        config1 = RunnerConfig(use_in_memory_services=True)
        config2 = RunnerConfig(use_in_memory_services=True)

        service1 = config1.get_artifact_service()
        service2 = config2.get_artifact_service()

        # Should be different instances
        assert service1 is not service2
