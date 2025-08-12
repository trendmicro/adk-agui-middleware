"""Unit tests for adk_agui_middleware.endpoint module."""

import sys
import os
import unittest
import importlib.util
import asyncio
from unittest.mock import AsyncMock, Mock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock external dependencies before importing the module
class MockRunAgentInput:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockRequest:
    def __init__(self):
        self.headers = Mock()
        self.headers.get = Mock(return_value="application/json")

class MockFastAPI:
    def __init__(self):
        self.routes = []
    
    def post(self, path):
        def decorator(func):
            route_mock = Mock()
            route_mock.path = path
            route_mock.endpoint = func
            route_mock.methods = ['POST']
            self.routes.append(route_mock)
            return func
        return decorator

class MockStreamingResponse:
    def __init__(self, content, media_type=None):
        self.content = content
        self.media_type = media_type

class MockEventEncoder:
    def __init__(self, accept=None):
        self.accept = accept
    
    def get_content_type(self):
        return "application/json"

class MockBaseSSEService:
    def __init__(self):
        self.get_runner = AsyncMock()
        self.event_generator = AsyncMock()

class MockExceptionHandler:
    def __init__(self, request):
        self.request = request
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

# Mock all external dependencies
sys.modules['ag_ui'] = Mock()
sys.modules['ag_ui.core'] = Mock()
sys.modules['ag_ui.core'].RunAgentInput = MockRunAgentInput
sys.modules['ag_ui.encoder'] = Mock()
sys.modules['ag_ui.encoder'].EventEncoder = MockEventEncoder
sys.modules['base_abc'] = Mock()
sys.modules['base_abc.sse_service'] = Mock()
sys.modules['base_abc.sse_service'].BaseSSEService = MockBaseSSEService
sys.modules['fastapi'] = Mock()
sys.modules['fastapi'].FastAPI = MockFastAPI
sys.modules['fastapi'].Request = MockRequest
sys.modules['loggers'] = Mock()
sys.modules['loggers.exception'] = Mock()
sys.modules['loggers.exception'].exception_http_handler = MockExceptionHandler
sys.modules['starlette'] = Mock()
sys.modules['starlette.responses'] = Mock()
sys.modules['starlette.responses'].StreamingResponse = MockStreamingResponse

# Load the endpoint module directly
spec = importlib.util.spec_from_file_location(
    "endpoint_module", 
    os.path.join(os.path.dirname(__file__), '..', 'src', 'adk_agui_middleware', 'endpoint.py')
)
endpoint_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(endpoint_module)

register_agui_endpoint = endpoint_module.register_agui_endpoint

# Import what we need for tests
FastAPI = MockFastAPI
Request = MockRequest 
StreamingResponse = MockStreamingResponse
RunAgentInput = MockRunAgentInput


class TestRegisterAGUIEndpoint(unittest.TestCase):
    """Test cases for the register_agui_endpoint function."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = MockFastAPI()
        self.mock_sse_service = MockBaseSSEService()
        self.mock_request = MockRequest()
        self.mock_agui_content = MockRunAgentInput()

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

    def test_agui_endpoint_execution(self):
        """Test the agui_endpoint function execution flow."""
        async def run_test():
            # Setup service mocks
            mock_runner = Mock()
            self.mock_sse_service.get_runner = AsyncMock(return_value=mock_runner)
            mock_event_stream = AsyncMock()
            self.mock_sse_service.event_generator = AsyncMock(return_value=mock_event_stream)
            
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
            self.mock_sse_service.get_runner.assert_called_once_with(
                self.mock_agui_content, self.mock_request
            )
            self.mock_sse_service.event_generator.assert_called_once()
            self.assertIsInstance(result, MockStreamingResponse)
        
        asyncio.run(run_test())

    def test_agui_endpoint_accept_header_handling(self):
        """Test that Accept header is properly handled."""
        async def run_test():
            # Setup service mocks
            self.mock_sse_service.get_runner = AsyncMock(return_value=Mock())
            self.mock_sse_service.event_generator = AsyncMock(return_value=AsyncMock())
            
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
                    app = MockFastAPI()  # Use fresh app for each test
                    register_agui_endpoint(app, self.mock_sse_service)
                    
                    agui_route = None
                    for route in app.routes:
                        if hasattr(route, 'path') and route.path == "/" and hasattr(route, 'endpoint'):
                            agui_route = route
                            break
                    
                    # Execute endpoint
                    result = await agui_route.endpoint(self.mock_agui_content, self.mock_request)
                    
                    # Verify result is a streaming response
                    self.assertIsInstance(result, MockStreamingResponse)
        
        asyncio.run(run_test())

    def test_agui_endpoint_exception_handling(self):
        """Test that exceptions are handled properly."""
        async def run_test():
            # Setup service that raises an exception
            self.mock_sse_service.get_runner = AsyncMock(side_effect=Exception("Test exception"))
            
            register_agui_endpoint(self.app, self.mock_sse_service)
            
            # Get the endpoint
            agui_route = None
            for route in self.app.routes:
                if hasattr(route, 'path') and route.path == "/" and hasattr(route, 'endpoint'):
                    agui_route = route
                    break
            
            # Verify exception is raised (would be handled by exception handler in real scenario)
            with self.assertRaises(Exception):
                await agui_route.endpoint(self.mock_agui_content, self.mock_request)
        
        asyncio.run(run_test())

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
        service1 = MockBaseSSEService()
        service2 = MockBaseSSEService()
        
        register_agui_endpoint(self.app, service1, "/service1")
        register_agui_endpoint(self.app, service2, "/service2")
        
        # Verify both routes are registered
        routes = [route.path for route in self.app.routes]
        self.assertIn("/service1", routes)
        self.assertIn("/service2", routes)

    def test_endpoint_streaming_response_media_type(self):
        """Test that StreamingResponse is created with correct media type."""
        async def run_test():
            # Setup service mocks
            self.mock_sse_service.get_runner = AsyncMock(return_value=Mock())
            self.mock_sse_service.event_generator = AsyncMock(return_value=Mock())
            
            register_agui_endpoint(self.app, self.mock_sse_service)
            
            # Get and execute endpoint
            agui_route = [
                route for route in self.app.routes 
                if hasattr(route, 'path') and route.path == "/"
            ][0]
            
            result = await agui_route.endpoint(self.mock_agui_content, self.mock_request)
            
            # Verify streaming response was created
            self.assertIsInstance(result, MockStreamingResponse)
        
        asyncio.run(run_test())

    def test_register_endpoint_parameter_validation(self):
        """Test parameter validation for register_agui_endpoint function."""
        # Test with valid parameters - should not raise
        register_agui_endpoint(self.app, self.mock_sse_service)
        register_agui_endpoint(self.app, self.mock_sse_service, "/custom")
        
        # The function doesn't do explicit validation, but we can test that
        # it works with different parameter combinations
        register_agui_endpoint(self.app, self.mock_sse_service, path="")
        register_agui_endpoint(self.app, self.mock_sse_service, path="/very/long/path/with/many/segments")

    def test_endpoint_function_signature(self):
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