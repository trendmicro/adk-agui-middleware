"""Additional tests for endpoint.py to boost coverage."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from ag_ui.encoder import EventEncoder
from fastapi import FastAPI, HTTPException, Request
from starlette.responses import StreamingResponse

from adk_agui_middleware.endpoint import register_agui_endpoint
from adk_agui_middleware.sse_service import SSEService

from .test_utils import BaseTestCase


class TestEndpointCoverage(BaseTestCase):
    """Additional tests for endpoint functionality to improve coverage."""

    def setUp(self):
        super().setUp()
        self.app = FastAPI()
        self.mock_service = Mock(spec=SSEService)

    def test_register_agui_endpoint_basic(self):
        """Test basic endpoint registration."""
        initial_route_count = len(self.app.routes)

        register_agui_endpoint(self.app, self.mock_service)

        # Should add one new route
        assert len(self.app.routes) == initial_route_count + 1

    def test_register_agui_endpoint_custom_path(self):
        """Test endpoint registration with custom path."""
        custom_path = "/custom/agui/endpoint"
        initial_route_count = len(self.app.routes)

        register_agui_endpoint(self.app, self.mock_service, custom_path)

        # Should add route at custom path
        assert len(self.app.routes) == initial_route_count + 1

        # Find the added route
        new_route = None
        for route in self.app.routes:
            if hasattr(route, "path") and route.path == custom_path:
                new_route = route
                break

        assert new_route is not None

    def test_register_agui_endpoint_default_path(self):
        """Test endpoint registration with default path."""
        initial_route_count = len(self.app.routes)

        register_agui_endpoint(self.app, self.mock_service)

        # Should add route at default path
        assert len(self.app.routes) == initial_route_count + 1

    @pytest.mark.asyncio
    async def test_endpoint_function_success(self):
        """Test successful endpoint execution."""
        # Register endpoint
        register_agui_endpoint(self.app, self.mock_service)

        # Get the endpoint function
        endpoint_func = None
        for route in self.app.routes:
            if (
                hasattr(route, "endpoint")
                and route.endpoint.__name__ == "agui_endpoint"
            ):
                endpoint_func = route.endpoint
                break

        assert endpoint_func is not None

        # Mock service behavior
        mock_runner = Mock()
        self.mock_service.get_runner = AsyncMock(return_value=mock_runner)

        mock_encoder = Mock(spec=EventEncoder)
        mock_encoder.get_content_type.return_value = "text/event-stream"

        # Mock event generator
        def mock_generator():
            yield b"data: test event\n\n"
            yield b"data: another event\n\n"

        self.mock_service.event_generator.return_value = mock_generator()

        # Create test input
        agui_content = self.factory.create_run_agent_input()
        request = Mock(spec=Request)
        request.headers = {"accept": "text/event-stream"}

        # Mock exception handler
        with patch(
            "adk_agui_middleware.endpoint.exception_http_handler"
        ) as mock_handler:
            with patch(
                "adk_agui_middleware.endpoint.EventEncoder", return_value=mock_encoder
            ):
                mock_handler.return_value.__aenter__ = AsyncMock()
                mock_handler.return_value.__aexit__ = AsyncMock()

                result = await endpoint_func(agui_content, request)

                assert isinstance(result, StreamingResponse)
                assert result.media_type == "text/event-stream"

    @pytest.mark.asyncio
    async def test_endpoint_function_exception_handling(self):
        """Test endpoint exception handling."""
        register_agui_endpoint(self.app, self.mock_service)

        endpoint_func = None
        for route in self.app.routes:
            if (
                hasattr(route, "endpoint")
                and route.endpoint.__name__ == "agui_endpoint"
            ):
                endpoint_func = route.endpoint
                break

        # Mock service to raise exception
        self.mock_service.get_runner = AsyncMock(side_effect=Exception("Service error"))

        agui_content = self.factory.create_run_agent_input()
        request = Mock(spec=Request)

        # Mock exception handler to raise HTTPException
        with patch(
            "adk_agui_middleware.endpoint.exception_http_handler"
        ) as mock_handler:
            mock_handler.return_value.__aenter__ = AsyncMock(
                side_effect=HTTPException(500, "Internal error")
            )

            with pytest.raises(HTTPException):
                await endpoint_func(agui_content, request)

    @pytest.mark.asyncio
    async def test_endpoint_encoder_initialization(self):
        """Test event encoder initialization in endpoint."""
        register_agui_endpoint(self.app, self.mock_service)

        endpoint_func = None
        for route in self.app.routes:
            if (
                hasattr(route, "endpoint")
                and route.endpoint.__name__ == "agui_endpoint"
            ):
                endpoint_func = route.endpoint
                break

        mock_runner = Mock()
        self.mock_service.get_runner = AsyncMock(return_value=mock_runner)

        mock_encoder = Mock(spec=EventEncoder)
        mock_encoder.get_content_type.return_value = "application/x-ndjson"

        self.mock_service.event_generator.return_value = iter([b"test"])

        agui_content = self.factory.create_run_agent_input()
        request = Mock(spec=Request)
        request.headers = {"accept": "application/x-ndjson"}

        with patch(
            "adk_agui_middleware.endpoint.exception_http_handler"
        ) as mock_handler:
            with patch(
                "adk_agui_middleware.endpoint.EventEncoder", return_value=mock_encoder
            ) as mock_encoder_class:
                mock_handler.return_value.__aenter__ = AsyncMock()
                mock_handler.return_value.__aexit__ = AsyncMock()

                result = await endpoint_func(agui_content, request)

                # Should initialize encoder based on request headers
                mock_encoder_class.assert_called_once_with(request.headers)
                assert isinstance(result, StreamingResponse)
                assert result.media_type == "application/x-ndjson"

    def test_endpoint_route_configuration(self):
        """Test endpoint route configuration details."""
        register_agui_endpoint(self.app, self.mock_service, "/test/endpoint")

        # Find the registered route
        target_route = None
        for route in self.app.routes:
            if hasattr(route, "path") and route.path == "/test/endpoint":
                target_route = route
                break

        assert target_route is not None
        assert hasattr(target_route, "endpoint")
        assert target_route.methods == {"POST"}

    @pytest.mark.asyncio
    async def test_streaming_response_content(self):
        """Test streaming response content generation."""
        register_agui_endpoint(self.app, self.mock_service)

        endpoint_func = None
        for route in self.app.routes:
            if (
                hasattr(route, "endpoint")
                and route.endpoint.__name__ == "agui_endpoint"
            ):
                endpoint_func = route.endpoint
                break

        mock_runner = Mock()
        self.mock_service.get_runner = AsyncMock(return_value=mock_runner)

        mock_encoder = Mock(spec=EventEncoder)
        mock_encoder.get_content_type.return_value = "text/event-stream"

        # Create test data
        test_events = [b"data: event1\n\n", b"data: event2\n\n", b"data: event3\n\n"]
        self.mock_service.event_generator.return_value = iter(test_events)

        agui_content = self.factory.create_run_agent_input()
        request = Mock(spec=Request)

        with patch(
            "adk_agui_middleware.endpoint.exception_http_handler"
        ) as mock_handler:
            with patch(
                "adk_agui_middleware.endpoint.EventEncoder", return_value=mock_encoder
            ):
                mock_handler.return_value.__aenter__ = AsyncMock()
                mock_handler.return_value.__aexit__ = AsyncMock()

                response = await endpoint_func(agui_content, request)

                # Collect streaming content
                content = []
                async for chunk in response.body_iterator:
                    content.append(chunk)

                # Should include all test events
                assert len(content) == 3
                assert content == test_events

    @pytest.mark.asyncio
    async def test_service_integration(self):
        """Test integration with SSE service."""
        register_agui_endpoint(self.app, self.mock_service, "/integration/test")

        endpoint_func = None
        for route in self.app.routes:
            if hasattr(route, "path") and route.path == "/integration/test":
                endpoint_func = route.endpoint
                break

        mock_runner = Mock()
        self.mock_service.get_runner = AsyncMock(return_value=mock_runner)

        mock_encoder = Mock(spec=EventEncoder)
        mock_encoder.get_content_type.return_value = "text/event-stream"

        agui_content = self.factory.create_run_agent_input()
        request = Mock(spec=Request)

        with patch(
            "adk_agui_middleware.endpoint.exception_http_handler"
        ) as mock_handler:
            with patch(
                "adk_agui_middleware.endpoint.EventEncoder", return_value=mock_encoder
            ):
                mock_handler.return_value.__aenter__ = AsyncMock()
                mock_handler.return_value.__aexit__ = AsyncMock()

                await endpoint_func(agui_content, request)

                # Verify service methods were called correctly
                self.mock_service.get_runner.assert_called_once_with(
                    agui_content, request
                )
                self.mock_service.event_generator.assert_called_once_with(
                    mock_runner, mock_encoder
                )

    def test_multiple_endpoint_registration(self):
        """Test registering multiple endpoints."""
        initial_count = len(self.app.routes)

        # Register multiple endpoints
        service1 = Mock(spec=SSEService)
        service2 = Mock(spec=SSEService)

        register_agui_endpoint(self.app, service1, "/endpoint1")
        register_agui_endpoint(self.app, service2, "/endpoint2")

        # Should add both routes
        assert len(self.app.routes) == initial_count + 2

        # Check both paths exist
        paths = [route.path for route in self.app.routes if hasattr(route, "path")]
        assert "/endpoint1" in paths
        assert "/endpoint2" in paths

    @pytest.mark.asyncio
    async def test_endpoint_error_responses(self):
        """Test endpoint error response handling."""
        register_agui_endpoint(self.app, self.mock_service)

        endpoint_func = None
        for route in self.app.routes:
            if (
                hasattr(route, "endpoint")
                and route.endpoint.__name__ == "agui_endpoint"
            ):
                endpoint_func = route.endpoint
                break

        agui_content = self.factory.create_run_agent_input()
        request = Mock(spec=Request)

        # Test different types of exceptions
        test_cases = [
            (ValueError("Invalid input"), 400),
            (RuntimeError("Internal error"), 500),
            (ConnectionError("Service unavailable"), 503),
        ]

        for exception, expected_status in test_cases:
            self.mock_service.get_runner = AsyncMock(side_effect=exception)

            with patch(
                "adk_agui_middleware.endpoint.exception_http_handler"
            ) as mock_handler:
                mock_handler.return_value.__aenter__ = AsyncMock(
                    side_effect=HTTPException(expected_status, str(exception))
                )

                with pytest.raises(HTTPException) as exc_info:
                    await endpoint_func(agui_content, request)

                assert exc_info.value.status_code == expected_status

    def test_endpoint_method_restriction(self):
        """Test that endpoint only accepts POST method."""
        register_agui_endpoint(self.app, self.mock_service)

        # Find the registered route
        agui_route = None
        for route in self.app.routes:
            if (
                hasattr(route, "endpoint")
                and route.endpoint.__name__ == "agui_endpoint"
            ):
                agui_route = route
                break

        assert agui_route is not None
        # Should only accept POST method
        assert agui_route.methods == {"POST"}
        # Should not accept GET, PUT, DELETE, etc.
        assert "GET" not in agui_route.methods
        assert "PUT" not in agui_route.methods
        assert "DELETE" not in agui_route.methods
