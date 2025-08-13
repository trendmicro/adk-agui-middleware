"""Unit tests for adk_agui_middleware.endpoint module."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, FastAPI, Request
from starlette.responses import StreamingResponse
from google.adk import Runner

from adk_agui_middleware.base_abc.sse_service import BaseSSEService
from adk_agui_middleware.endpoint import register_agui_endpoint


class TestRegisterAGUIEndpoint(unittest.TestCase):
    """Test cases for register_agui_endpoint function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sse_service = Mock(spec=BaseSSEService)
        self.mock_app = Mock(spec=FastAPI)
        self.mock_request = Mock(spec=Request)
        self.mock_request.headers = {"accept": "text/event-stream"}

    def test_register_agui_endpoint_fastapi(self):
        """Test registering endpoint with FastAPI instance."""
        register_agui_endpoint(self.mock_app, self.mock_sse_service)
        
        # Verify that @app.post was called
        self.mock_app.post.assert_called_once_with("/")

    def test_register_agui_endpoint_custom_path(self):
        """Test registering endpoint with custom path."""
        custom_path = "/custom/path"
        register_agui_endpoint(self.mock_app, self.mock_sse_service, path=custom_path)
        
        # Verify that @app.post was called with custom path
        self.mock_app.post.assert_called_once_with(custom_path)

    def test_register_agui_endpoint_api_router(self):
        """Test registering endpoint with APIRouter instance."""
        mock_router = Mock(spec=APIRouter)
        register_agui_endpoint(mock_router, self.mock_sse_service)
        
        # Verify that router.post was called
        mock_router.post.assert_called_once_with("/")

    def create_agui_content(self):
        """Helper to create a test RunAgentInput instance."""
        return RunAgentInput(
            thread_id="test_thread",
            run_id="test_run",
            state={},
            messages=[],
            tools=[],
            context=[],
            forwarded_props={}
        )

    @patch('adk_agui_middleware.endpoint.exception_http_handler')
    async def test_agui_endpoint_successful_request(self, mock_exception_handler):
        """Test successful AGUI endpoint request processing."""
        # Setup mocks
        agui_content = self.create_agui_content()
        mock_runner = Mock(spec=Runner)
        mock_encoder = Mock(spec=EventEncoder)
        mock_encoder.get_content_type.return_value = "text/event-stream"
        
        self.mock_sse_service.get_runner = AsyncMock(return_value=mock_runner)
        self.mock_sse_service.event_generator.return_value = iter([b"data: test\n\n"])
        
        # Create a real FastAPI app to test endpoint registration
        app = FastAPI()
        register_agui_endpoint(app, self.mock_sse_service)
        
        # Get the registered endpoint function
        endpoint_func = None
        for route in app.routes:
            if hasattr(route, 'endpoint'):
                endpoint_func = route.endpoint
                break
        
        self.assertIsNotNone(endpoint_func)
        
        # Mock EventEncoder creation
        with patch('adk_agui_middleware.endpoint.EventEncoder', return_value=mock_encoder):
            # Mock exception handler as async context manager
            mock_exception_handler.return_value.__aenter__ = AsyncMock()
            mock_exception_handler.return_value.__aexit__ = AsyncMock()
            
            # Call the endpoint function directly
            response = await endpoint_func(agui_content, self.mock_request)
        
        # Verify the response
        self.assertIsInstance(response, StreamingResponse)
        self.mock_sse_service.get_runner.assert_called_once_with(agui_content, self.mock_request)
        mock_encoder.get_content_type.assert_called_once()

    @patch('adk_agui_middleware.endpoint.exception_http_handler')
    async def test_agui_endpoint_encoder_creation(self, mock_exception_handler):
        """Test that EventEncoder is created with correct Accept header."""
        agui_content = self.create_agui_content()
        mock_runner = Mock(spec=Runner)
        
        self.mock_sse_service.get_runner = AsyncMock(return_value=mock_runner)
        self.mock_sse_service.event_generator.return_value = iter([])
        
        # Set specific accept header
        self.mock_request.headers = {"accept": "application/json"}
        
        # Create a real FastAPI app
        app = FastAPI()
        register_agui_endpoint(app, self.mock_sse_service)
        
        # Get the registered endpoint function
        endpoint_func = None
        for route in app.routes:
            if hasattr(route, 'endpoint'):
                endpoint_func = route.endpoint
                break
        
        # Mock exception handler
        mock_exception_handler.return_value.__aenter__ = AsyncMock()
        mock_exception_handler.return_value.__aexit__ = AsyncMock()
        
        # Test encoder creation with accept header
        with patch('adk_agui_middleware.endpoint.EventEncoder') as mock_encoder_class:
            mock_encoder_instance = Mock()
            mock_encoder_instance.get_content_type.return_value = "application/json"
            mock_encoder_class.return_value = mock_encoder_instance
            
            await endpoint_func(agui_content, self.mock_request)
            
            # Verify EventEncoder was created with correct accept header
            mock_encoder_class.assert_called_once_with(accept="application/json")

    @patch('adk_agui_middleware.endpoint.exception_http_handler')
    async def test_agui_endpoint_no_accept_header(self, mock_exception_handler):
        """Test endpoint behavior when Accept header is missing."""
        agui_content = self.create_agui_content()
        mock_runner = Mock(spec=Runner)
        
        self.mock_sse_service.get_runner = AsyncMock(return_value=mock_runner)
        self.mock_sse_service.event_generator.return_value = iter([])
        
        # Remove accept header
        self.mock_request.headers = {}
        
        app = FastAPI()
        register_agui_endpoint(app, self.mock_sse_service)
        
        endpoint_func = None
        for route in app.routes:
            if hasattr(route, 'endpoint'):
                endpoint_func = route.endpoint
                break
        
        # Mock exception handler
        mock_exception_handler.return_value.__aenter__ = AsyncMock()
        mock_exception_handler.return_value.__aexit__ = AsyncMock()
        
        with patch('adk_agui_middleware.endpoint.EventEncoder') as mock_encoder_class:
            mock_encoder_instance = Mock()
            mock_encoder_instance.get_content_type.return_value = "text/event-stream"
            mock_encoder_class.return_value = mock_encoder_instance
            
            await endpoint_func(agui_content, self.mock_request)
            
            # Verify EventEncoder was created with None (default)
            mock_encoder_class.assert_called_once_with(accept=None)

    @patch('adk_agui_middleware.endpoint.exception_http_handler')
    async def test_agui_endpoint_streaming_response_properties(self, mock_exception_handler):
        """Test that StreamingResponse is created with correct properties."""
        agui_content = self.create_agui_content()
        mock_runner = Mock(spec=Runner)
        mock_encoder = Mock(spec=EventEncoder)
        
        # Setup return values
        mock_encoder.get_content_type.return_value = "text/event-stream"
        test_content = [b"data: test1\n\n", b"data: test2\n\n"]
        
        self.mock_sse_service.get_runner = AsyncMock(return_value=mock_runner)
        self.mock_sse_service.event_generator.return_value = iter(test_content)
        
        app = FastAPI()
        register_agui_endpoint(app, self.mock_sse_service)
        
        endpoint_func = None
        for route in app.routes:
            if hasattr(route, 'endpoint'):
                endpoint_func = route.endpoint
                break
        
        # Mock exception handler
        mock_exception_handler.return_value.__aenter__ = AsyncMock()
        mock_exception_handler.return_value.__aexit__ = AsyncMock()
        
        with patch('adk_agui_middleware.endpoint.EventEncoder', return_value=mock_encoder):
            response = await endpoint_func(agui_content, self.mock_request)
        
        # Verify response properties
        self.assertIsInstance(response, StreamingResponse)
        self.assertEqual(response.media_type, "text/event-stream")
        
        # Verify event_generator was called with correct arguments
        self.mock_sse_service.event_generator.assert_called_once_with(mock_runner, mock_encoder)

    async def test_endpoint_function_signature(self):
        """Test that the registered endpoint has correct function signature."""
        app = FastAPI()
        register_agui_endpoint(app, self.mock_sse_service)
        
        # Get the registered endpoint function
        endpoint_func = None
        for route in app.routes:
            if hasattr(route, 'endpoint'):
                endpoint_func = route.endpoint
                break
        
        self.assertIsNotNone(endpoint_func)
        
        # Check function name and annotations
        self.assertEqual(endpoint_func.__name__, "agui_endpoint")
        
        # The function should be async
        import asyncio
        self.assertTrue(asyncio.iscoroutinefunction(endpoint_func))

    def test_multiple_endpoint_registrations(self):
        """Test registering multiple endpoints on same app."""
        app = FastAPI()
        initial_route_count = len(app.routes)
        sse_service1 = Mock(spec=BaseSSEService)
        sse_service2 = Mock(spec=BaseSSEService)
        
        register_agui_endpoint(app, sse_service1, path="/endpoint1")
        register_agui_endpoint(app, sse_service2, path="/endpoint2")
        
        # Should have added 2 endpoints
        self.assertEqual(len(app.routes), initial_route_count + 2)

    def test_endpoint_route_configuration(self):
        """Test that the route is configured correctly."""
        app = FastAPI()
        initial_route_count = len(app.routes)
        custom_path = "/custom/agui"
        
        register_agui_endpoint(app, self.mock_sse_service, path=custom_path)
        
        # Verify route was added
        self.assertEqual(len(app.routes), initial_route_count + 1)
        
        # Find our custom route
        custom_route = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == custom_path:
                custom_route = route
                break
        
        self.assertIsNotNone(custom_route)
        self.assertIn("POST", custom_route.methods)

    @patch('adk_agui_middleware.endpoint.exception_http_handler')
    async def test_exception_handler_usage(self, mock_exception_handler):
        """Test that exception_http_handler is used correctly."""
        agui_content = self.create_agui_content()
        
        app = FastAPI()
        register_agui_endpoint(app, self.mock_sse_service)
        
        endpoint_func = None
        for route in app.routes:
            if hasattr(route, 'endpoint'):
                endpoint_func = route.endpoint
                break
        
        # Mock exception handler as async context manager
        mock_context = AsyncMock()
        mock_exception_handler.return_value = mock_context
        
        # Mock other dependencies
        with patch('adk_agui_middleware.endpoint.EventEncoder'):
            self.mock_sse_service.get_runner = AsyncMock()
            self.mock_sse_service.event_generator.return_value = iter([])
            
            await endpoint_func(agui_content, self.mock_request)
        
        # Verify exception handler was called with request
        mock_exception_handler.assert_called_once_with(self.mock_request)
        mock_context.__aenter__.assert_called_once()
        mock_context.__aexit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()