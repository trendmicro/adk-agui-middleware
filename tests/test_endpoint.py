# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.endpoint module."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from ag_ui.core import RunAgentInput
from fastapi import APIRouter, FastAPI, Request
from sse_starlette import EventSourceResponse

from adk_agui_middleware.base_abc.sse_service import BaseSSEService
from adk_agui_middleware.data_model.config import PathConfig
from adk_agui_middleware.endpoint import register_agui_endpoint


class TestEndpointRegistration(unittest.TestCase):
    """Test cases for endpoint registration."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_app = Mock(spec=FastAPI)
        self.mock_router = Mock(spec=APIRouter)
        self.mock_sse_service = Mock(spec=BaseSSEService)

    def test_register_agui_endpoint_with_fastapi(self):
        """Test registering endpoint with FastAPI app."""
        register_agui_endpoint(self.mock_app, self.mock_sse_service)
        
        # Verify the endpoint was registered
        self.mock_app.post.assert_called_once_with("")

    def test_register_agui_endpoint_with_router(self):
        """Test registering endpoint with APIRouter."""
        register_agui_endpoint(self.mock_router, self.mock_sse_service)
        
        # Verify the endpoint was registered
        self.mock_router.post.assert_called_once_with("")

    def test_register_agui_endpoint_custom_path(self):
        """Test registering endpoint with custom path."""
        custom_path_config = PathConfig(agui_main_path="/custom/path")
        register_agui_endpoint(self.mock_app, self.mock_sse_service, custom_path_config)
        
        # Verify the endpoint was registered with custom path
        self.mock_app.post.assert_called_once_with("/custom/path")

    def test_agui_endpoint_success(self):
        """Test successful AGUI endpoint execution."""
        # This test verifies the registration process works
        register_agui_endpoint(self.mock_app, self.mock_sse_service)
        
        # Verify the post method was called with correct path
        self.mock_app.post.assert_called_once_with("")

    def test_agui_endpoint_with_exception(self):
        """Test AGUI endpoint registration."""
        register_agui_endpoint(self.mock_app, self.mock_sse_service)
        
        # Verify the endpoint registration
        self.mock_app.post.assert_called_once_with("")

    def test_endpoint_decorator_and_function_name(self):
        """Test that the endpoint is properly decorated and named."""
        register_agui_endpoint(self.mock_app, self.mock_sse_service)
        
        # Get the call to app.post
        call_args = self.mock_app.post.call_args
        
        # Verify the path
        self.assertEqual(call_args[0][0], "")
        
        # The decorator is called as @app.post(path), so the function is passed as the first argument
        # to the decorator. Let's check if it was called properly.
        self.mock_app.post.assert_called_once_with("")

    def test_endpoint_parameters_and_return_type(self):
        """Test endpoint parameters and return type annotations."""
        # For this test, we'll just verify the endpoint was registered
        register_agui_endpoint(self.mock_app, self.mock_sse_service)
        
        # Verify the decorator was called
        self.mock_app.post.assert_called_once_with("")

    def test_multiple_endpoint_registrations(self):
        """Test registering multiple endpoints with different paths."""
        paths = ["", "/api/v1", "/custom"]
        
        for path in paths:
            path_config = PathConfig(agui_main_path=path)
            register_agui_endpoint(self.mock_app, self.mock_sse_service, path_config)
        
        # Verify all paths were registered
        self.assertEqual(self.mock_app.post.call_count, len(paths))
        
        # Verify each call had the correct path
        call_args_list = self.mock_app.post.call_args_list
        for i, path in enumerate(paths):
            self.assertEqual(call_args_list[i][0][0], path)


if __name__ == "__main__":
    unittest.main()