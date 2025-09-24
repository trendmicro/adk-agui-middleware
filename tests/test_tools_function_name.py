# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Unit tests for adk_agui_middleware.tools.function_name module."""

import importlib.util
import os
import sys
import unittest

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Load the function_name module directly
spec = importlib.util.spec_from_file_location(
    "function_name_module",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "adk_agui_middleware",
        "tools",
        "function_name.py",
    ),
)
function_name_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(function_name_module)

_should_skip_function = function_name_module._should_skip_function
_format_function_name = function_name_module._format_function_name
extract_caller_name = function_name_module.extract_caller_name


class TestFunctionNameUtils(unittest.TestCase):
    """Test cases for function name utilities."""

    def test_should_skip_function_skip_logging(self):
        """Test that logging functions are skipped."""
        self.assertTrue(_should_skip_function("get_function_name"))
        self.assertTrue(_should_skip_function("debug"))
        self.assertTrue(_should_skip_function("wrapper"))

    def test_should_skip_function_include_meaningful(self):
        """Test that meaningful functions are not skipped."""
        self.assertFalse(_should_skip_function("__init__"))
        self.assertFalse(_should_skip_function("my_function"))

    def test_format_function_name_standalone(self):
        """Test formatting standalone functions."""
        result = _format_function_name("test_func", {"param": "value"})
        self.assertEqual(result, "test_func")

    def test_extract_caller_name_basic(self):
        """Test basic function name extraction."""

        def test_function():
            return extract_caller_name()

        result = test_function()
        # Should return some function name (may be test runner function)
        self.assertIsInstance(result, str)
        self.assertNotEqual(result, "unknown_function")


if __name__ == "__main__":
    unittest.main()
