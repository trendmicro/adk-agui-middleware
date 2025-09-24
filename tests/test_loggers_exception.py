# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.loggers.exception module."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException, Request

from adk_agui_middleware.loggers.exception import (
    create_common_http_exception, create_internal_server_error_exception,
    http_exception_handler)


class TestHTTPExceptionHandling(unittest.TestCase):
    """Test cases for HTTP exception handling functions."""

    @patch("time.time")
    def test_get_common_http_exception(self, mock_time):
        """Test creating common HTTP exception."""
        mock_time.return_value = 1234567890
        status_code = 400
        error_message = "Bad Request"
        error_description = {"field": "invalid_value"}
        
        result = create_common_http_exception(status_code, error_message, error_description)
        
        self.assertIsInstance(result, HTTPException)
        self.assertEqual(result.status_code, status_code)
        self.assertEqual(result.detail["error"], error_message)
        self.assertEqual(result.detail["error_description"], error_description)
        self.assertEqual(result.detail["timestamp"], 1234567890)

    @patch("time.time")
    def test_get_http_internal_server_error_exception(self, mock_time):
        """Test creating internal server error exception."""
        mock_time.return_value = 1234567890
        error_description = {"message": "Internal error"}
        
        result = create_internal_server_error_exception(error_description)
        
        self.assertIsInstance(result, HTTPException)
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.detail["error"], "Internal Server Error.")
        self.assertEqual(result.detail["error_description"], error_description)

    @patch("adk_agui_middleware.loggers.exception.record_request_log")
    async def test_exception_http_handler_success(self, mock_record_request_log):
        """Test exception handler with successful execution."""
        mock_request = Mock(spec=Request)
        mock_record_request_log.return_value = AsyncMock()
        
        async with http_exception_handler(mock_request):
            # Simulate successful operation
            pass
        
        mock_record_request_log.assert_called_once_with(mock_request)

    @patch("adk_agui_middleware.loggers.exception.record_request_error_log")
    @patch("adk_agui_middleware.loggers.exception.record_request_log")
    async def test_exception_http_handler_http_exception(self, mock_record_request_log, mock_record_error_log):
        """Test exception handler with HTTP exception."""
        mock_request = Mock(spec=Request)
        mock_record_request_log.return_value = AsyncMock()
        mock_record_error_log.return_value = AsyncMock()
        
        http_exception = HTTPException(status_code=404, detail="Not found")
        
        with self.assertRaises(HTTPException) as context:
            async with http_exception_handler(mock_request):
                raise http_exception
        
        self.assertEqual(context.exception, http_exception)
        mock_record_request_log.assert_called_once_with(mock_request)
        mock_record_error_log.assert_called_once_with(mock_request, http_exception)

    @patch("adk_agui_middleware.loggers.exception.record_request_error_log")
    @patch("adk_agui_middleware.loggers.exception.record_request_log")
    async def test_exception_http_handler_general_exception(self, mock_record_request_log, mock_record_error_log):
        """Test exception handler with general exception."""
        mock_request = Mock(spec=Request)
        mock_record_request_log.return_value = AsyncMock()
        mock_record_error_log.return_value = AsyncMock()
        
        original_exception = ValueError("Test error")
        
        with self.assertRaises(HTTPException) as context:
            async with http_exception_handler(mock_request):
                raise original_exception
        
        # Should convert to HTTP 500 error
        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.detail["error"], "Internal Server Error.")
        self.assertIn("error_message", context.exception.detail["error_description"])
        
        mock_record_request_log.assert_called_once_with(mock_request)
        mock_record_error_log.assert_called_once_with(mock_request, original_exception)

    def test_error_model_structure(self):
        """Test that the error model has the correct structure."""
        error_description = {"detail": "test"}
        exception = create_common_http_exception(400, "Test Error", error_description)
        
        detail = exception.detail
        
        # Check required fields
        self.assertIn("error", detail)
        self.assertIn("error_description", detail)
        self.assertIn("timestamp", detail)
        
        # Check values
        self.assertEqual(detail["error"], "Test Error")
        self.assertEqual(detail["error_description"], error_description)
        self.assertIsInstance(detail["timestamp"], int)

    def test_different_status_codes(self):
        """Test creating exceptions with different status codes."""
        status_codes = [400, 401, 403, 404, 422, 500]
        
        for status_code in status_codes:
            exception = create_common_http_exception(
                status_code, f"Error {status_code}", {"code": status_code}
            )
            
            self.assertEqual(exception.status_code, status_code)
            self.assertEqual(exception.detail["error"], f"Error {status_code}")

    def test_empty_error_description(self):
        """Test creating exception with empty error description."""
        exception = create_common_http_exception(400, "Error", {})
        
        self.assertEqual(exception.detail["error_description"], {})

    def test_complex_error_description(self):
        """Test creating exception with complex error description."""
        complex_description = {
            "field_errors": [
                {"field": "email", "message": "Invalid format"},
                {"field": "age", "message": "Must be positive"}
            ],
            "context": {"user_id": "123", "request_id": "abc"},
            "suggestions": ["Check email format", "Verify age value"]
        }
        
        exception = create_common_http_exception(422, "Validation Error", complex_description)
        
        self.assertEqual(exception.detail["error_description"], complex_description)


if __name__ == "__main__":
    unittest.main()