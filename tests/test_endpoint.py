"""Unit tests for adk_agui_middleware.endpoint module."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from ag_ui.core import RunAgentInput
from fastapi import FastAPI, Request
from starlette.responses import StreamingResponse

from adk_agui_middleware.endpoint import register_agui_endpoint


class TestRegisterAGUIEndpoint(unittest.TestCase):
    """Test cases for the register_agui_endpoint function."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.mock_sse_service = Mock()
        self.mock_request = Mock(spec=Request)
        self.mock_agui_content = Mock(spec=RunAgentInput)

    def test_register_agui_endpoint_default_path(self):
        """Test registering endpoint with default path."""
        register_agui_endpoint(self.app, self.mock_sse_service)
        
        # Check that a route was registered
        routes = [route.path for route in self.app.routes]
        self.assertIn("/", routes)
        
        # Verify it's a POST route
        post_routes = [
            route for route in self.app.routes 
            if hasattr(route, 'methods') and 'POST' in route.methods
        ]
        self.assertTrue(len(post_routes) > 0)

    def test_register_agui_endpoint_custom_path(self):
        """Test registering endpoint with custom path."""
        custom_path = "/api/agents"
        register_agui_endpoint(self.app, self.mock_sse_service, path=custom_path)
        
        routes = [route.path for route in self.app.routes]
        self.assertIn(custom_path, routes)

    @patch('adk_agui_middleware.endpoint.exception_http_handler')
    @patch('adk_agui_middleware.endpoint.EventEncoder')
    @patch('adk_agui_middleware.endpoint.StreamingResponse')
    async def test_agui_endpoint_execution(
        self, mock_streaming_response, mock_event_encoder, mock_exception_handler
    ):
        """Test the agui_endpoint function execution flow."""
        # Setup mocks
        mock_encoder = Mock()
        mock_encoder.get_content_type.return_value = "application/json"
        mock_event_encoder.return_value = mock_encoder
        
        mock_runner = Mock()
        self.mock_sse_service.get_runner = AsyncMock(return_value=mock_runner)
        
        mock_event_stream = AsyncMock()
        self.mock_sse_service.event_generator = AsyncMock(return_value=mock_event_stream)
        
        mock_streaming_response_instance = Mock(spec=StreamingResponse)
        mock_streaming_response.return_value = mock_streaming_response_instance
        
        self.mock_request.headers.get.return_value = "application/json"
        
        # Setup exception handler context manager
        mock_context = Mock()
        mock_context.__aenter__ = AsyncMock()
        mock_context.__aexit__ = AsyncMock()
        mock_exception_handler.return_value = mock_context
        
        # Register the endpoint
        register_agui_endpoint(self.app, self.mock_sse_service)
        
        # Get the registered endpoint function
        agui_route = None
        for route in self.app.routes:
            if hasattr(route, 'path') and route.path == "/" and hasattr(route, 'endpoint'):
                agui_route = route
                break
        
        self.assertIsNotNone(agui_route)
        
        # Execute the endpoint function
        result = await agui_route.endpoint(self.mock_agui_content, self.mock_request)
        
        # Verify the flow
        mock_event_encoder.assert_called_once_with(accept="application/json")
        self.mock_sse_service.get_runner.assert_called_once_with(
            self.mock_agui_content, self.mock_request
        )
        self.mock_sse_service.event_generator.assert_called_once_with(
            mock_runner, mock_encoder
        )
        mock_streaming_response.assert_called_once_with(
            mock_event_stream, media_type="application/json"
        )
        self.assertEqual(result, mock_streaming_response_instance)

    @patch('adk_agui_middleware.endpoint.exception_http_handler')
    @patch('adk_agui_middleware.endpoint.EventEncoder')
    async def test_agui_endpoint_accept_header_handling(
        self, mock_event_encoder, mock_exception_handler
    ):
        """Test that Accept header is properly passed to EventEncoder."""
        # Setup mocks
        mock_encoder = Mock()
        mock_event_encoder.return_value = mock_encoder
        
        self.mock_sse_service.get_runner = AsyncMock(return_value=Mock())
        self.mock_sse_service.event_generator = AsyncMock(return_value=AsyncMock())
        
        # Setup exception handler
        mock_context = Mock()
        mock_context.__aenter__ = AsyncMock()
        mock_context.__aexit__ = AsyncMock()
        mock_exception_handler.return_value = mock_context
        
        # Test different Accept header values
        test_cases = [
            "text/event-stream",
            "application/json", 
            "text/plain",
            None
        ]
        
        for accept_header in test_cases:
            with self.subTest(accept_header=accept_header):
                self.mock_request.headers.get.return_value = accept_header
                
                # Register and get endpoint
                app = FastAPI()  # Use fresh app for each test
                register_agui_endpoint(app, self.mock_sse_service)
                
                agui_route = None
                for route in app.routes:
                    if hasattr(route, 'path') and route.path == "/" and hasattr(route, 'endpoint'):
                        agui_route = route
                        break
                
                # Execute endpoint
                await agui_route.endpoint(self.mock_agui_content, self.mock_request)
                
                # Verify EventEncoder was called with correct accept header
                mock_event_encoder.assert_called_with(accept=accept_header)
                mock_event_encoder.reset_mock()

    @patch('adk_agui_middleware.endpoint.exception_http_handler')
    async def test_agui_endpoint_exception_handling(self, mock_exception_handler):
        """Test that exceptions are handled by exception_http_handler."""
        # Setup exception handler that raises an exception
        mock_context = Mock()
        mock_context.__aenter__ = AsyncMock(side_effect=Exception("Test exception"))
        mock_context.__aexit__ = AsyncMock()
        mock_exception_handler.return_value = mock_context
        
        register_agui_endpoint(self.app, self.mock_sse_service)
        
        # Get the endpoint
        agui_route = None
        for route in self.app.routes:
            if hasattr(route, 'path') and route.path == "/" and hasattr(route, 'endpoint'):
                agui_route = route
                break
        
        # Verify exception is raised (would be handled by FastAPI in real scenario)
        with self.assertRaises(Exception):
            await agui_route.endpoint(self.mock_agui_content, self.mock_request)
        
        # Verify exception handler was used
        mock_exception_handler.assert_called_once_with(self.mock_request)

    def test_multiple_endpoint_registrations(self):
        """Test registering multiple endpoints with different paths."""
        paths = ["/api/v1", "/api/v2", "/agents"]
        
        for path in paths:
            register_agui_endpoint(self.app, self.mock_sse_service, path=path)
        
        registered_paths = [route.path for route in self.app.routes]
        
        for path in paths:
            self.assertIn(path, registered_paths)

    def test_endpoint_registration_with_different_services(self):
        """Test registering endpoints with different SSE services."""
        service1 = Mock()
        service2 = Mock()
        
        register_agui_endpoint(self.app, service1, "/service1")
        register_agui_endpoint(self.app, service2, "/service2")
        
        # Verify both routes are registered
        routes = [route.path for route in self.app.routes]
        self.assertIn("/service1", routes)
        self.assertIn("/service2", routes)

    @patch('adk_agui_middleware.endpoint.exception_http_handler')
    @patch('adk_agui_middleware.endpoint.EventEncoder')
    @patch('adk_agui_middleware.endpoint.StreamingResponse')
    async def test_endpoint_streaming_response_media_type(
        self, mock_streaming_response, mock_event_encoder, mock_exception_handler
    ):
        """Test that StreamingResponse gets correct media type from encoder."""
        # Setup mocks
        mock_encoder = Mock()
        test_media_type = "custom/media-type"
        mock_encoder.get_content_type.return_value = test_media_type
        mock_event_encoder.return_value = mock_encoder
        
        self.mock_sse_service.get_runner = AsyncMock(return_value=Mock())
        self.mock_sse_service.event_generator = AsyncMock(return_value=Mock())
        
        mock_streaming_response_instance = Mock()
        mock_streaming_response.return_value = mock_streaming_response_instance
        
        # Setup exception handler
        mock_context = Mock()
        mock_context.__aenter__ = AsyncMock()
        mock_context.__aexit__ = AsyncMock()
        mock_exception_handler.return_value = mock_context
        
        self.mock_request.headers.get.return_value = "application/json"
        
        register_agui_endpoint(self.app, self.mock_sse_service)
        
        # Get and execute endpoint
        agui_route = [
            route for route in self.app.routes 
            if hasattr(route, 'path') and route.path == "/"
        ][0]
        
        await agui_route.endpoint(self.mock_agui_content, self.mock_request)
        
        # Verify media type was passed correctly
        mock_streaming_response.assert_called_once()
        call_args = mock_streaming_response.call_args
        self.assertEqual(call_args[1]['media_type'], test_media_type)

    def test_register_endpoint_parameter_validation(self):
        """Test parameter validation for register_agui_endpoint function."""
        # Test with valid parameters - should not raise
        register_agui_endpoint(self.app, self.mock_sse_service)
        register_agui_endpoint(self.app, self.mock_sse_service, "/custom")
        
        # The function doesn't do explicit validation, but we can test that
        # it works with different parameter combinations
        register_agui_endpoint(self.app, self.mock_sse_service, path="")
        register_agui_endpoint(self.app, self.mock_sse_service, path="/very/long/path/with/many/segments")

    async def test_endpoint_function_signature(self):
        """Test that the registered endpoint function has correct signature."""
        register_agui_endpoint(self.app, self.mock_sse_service)
        
        # Get the registered route
        agui_route = None
        for route in self.app.routes:
            if hasattr(route, 'path') and route.path == "/" and hasattr(route, 'endpoint'):
                agui_route = route
                break
        
        self.assertIsNotNone(agui_route)
        
        # Check that the endpoint function exists and is callable
        self.assertTrue(callable(agui_route.endpoint))
        
        # Function should accept agui_content and request parameters
        # This is implicitly tested by other test methods that call the endpoint


if __name__ == '__main__':
    unittest.main()