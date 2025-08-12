"""Unit tests for adk_agui_middleware.tools.function_name module."""

import inspect
import unittest
from unittest.mock import MagicMock, Mock, patch

from adk_agui_middleware.tools.function_name import (
    _collect_valid_functions,
    _format_function_name,
    _should_skip_function,
    get_function_name,
)


class TestShouldSkipFunction(unittest.TestCase):
    """Test cases for _should_skip_function function."""

    def test_skip_logging_functions(self):
        """Test that logging functions are skipped."""
        skip_functions = [
            "get_function_name",
            "_record_raw_data_log", 
            "_create_and_log_message",
            "log_call",
            "trace",
            "debug"
        ]
        
        for func_name in skip_functions:
            with self.subTest(func_name=func_name):
                self.assertTrue(_should_skip_function(func_name))

    def test_skip_wrapper_functions(self):
        """Test that wrapper functions are skipped."""
        skip_functions = ["wrapper", "__call__", "<lambda>", "<module>"]
        
        for func_name in skip_functions:
            with self.subTest(func_name=func_name):
                self.assertTrue(_should_skip_function(func_name))

    def test_skip_comprehensions(self):
        """Test that comprehension functions are skipped."""
        skip_functions = ["<listcomp>", "<dictcomp>", "<setcomp>"]
        
        for func_name in skip_functions:
            with self.subTest(func_name=func_name):
                self.assertTrue(_should_skip_function(func_name))

    def test_include_meaningful_dunder_methods(self):
        """Test that meaningful dunder methods are not skipped."""
        include_functions = ["__init__", "__new__", "__enter__", "__exit__"]
        
        for func_name in include_functions:
            with self.subTest(func_name=func_name):
                self.assertFalse(_should_skip_function(func_name))

    def test_skip_other_dunder_methods(self):
        """Test that other dunder methods are skipped."""
        skip_functions = ["__str__", "__repr__", "__eq__", "__hash__", "__len__"]
        
        for func_name in skip_functions:
            with self.subTest(func_name=func_name):
                self.assertTrue(_should_skip_function(func_name))

    def test_include_regular_functions(self):
        """Test that regular functions are not skipped."""
        include_functions = ["my_function", "calculate", "process_data", "main"]
        
        for func_name in include_functions:
            with self.subTest(func_name=func_name):
                self.assertFalse(_should_skip_function(func_name))


class TestFormatFunctionName(unittest.TestCase):
    """Test cases for _format_function_name function."""

    def test_instance_method_formatting(self):
        """Test formatting instance methods with 'self'."""
        mock_self = Mock()
        mock_self.__class__.__name__ = "MyClass"
        frame_locals = {"self": mock_self, "param": "value"}
        
        result = _format_function_name("my_method", frame_locals)
        
        self.assertEqual(result, "MyClass.my_method")

    def test_class_method_formatting(self):
        """Test formatting class methods with 'cls'."""
        mock_cls = Mock()
        mock_cls.__name__ = "MyClass"
        frame_locals = {"cls": mock_cls, "param": "value"}
        
        result = _format_function_name("class_method", frame_locals)
        
        self.assertEqual(result, "MyClass.class_method")

    def test_standalone_function_formatting(self):
        """Test formatting standalone functions."""
        frame_locals = {"param": "value", "other": "data"}
        
        result = _format_function_name("standalone_function", frame_locals)
        
        self.assertEqual(result, "standalone_function")

    def test_empty_locals_formatting(self):
        """Test formatting with empty frame locals."""
        frame_locals = {}
        
        result = _format_function_name("function_name", frame_locals)
        
        self.assertEqual(result, "function_name")

    def test_self_and_cls_both_present(self):
        """Test formatting when both 'self' and 'cls' are present."""
        mock_self = Mock()
        mock_self.__class__.__name__ = "InstanceClass"
        mock_cls = Mock()
        mock_cls.__name__ = "ClassMethodClass"
        
        frame_locals = {"self": mock_self, "cls": mock_cls}
        
        # Should prioritize 'self' over 'cls'
        result = _format_function_name("method", frame_locals)
        
        self.assertEqual(result, "InstanceClass.method")


class TestCollectValidFunctions(unittest.TestCase):
    """Test cases for _collect_valid_functions function."""

    def test_collect_valid_functions_basic(self):
        """Test collecting valid functions from stack frames."""
        # Create mock frame info objects
        frame_info1 = Mock()
        frame_info1.function = "valid_function"
        frame_info1.frame.f_locals = {}
        
        frame_info2 = Mock()
        frame_info2.function = "wrapper"  # Should be skipped
        frame_info2.frame.f_locals = {}
        
        frame_info3 = Mock()
        frame_info3.function = "another_valid"
        frame_info3.frame.f_locals = {}
        
        stack_frames = [frame_info1, frame_info2, frame_info3]
        
        result = _collect_valid_functions(stack_frames)
        
        expected = ["valid_function", "another_valid"]
        self.assertEqual(result, expected)

    def test_collect_with_class_methods(self):
        """Test collecting functions with class context."""
        # Mock frame with instance method
        frame_info1 = Mock()
        frame_info1.function = "instance_method"
        mock_self = Mock()
        mock_self.__class__.__name__ = "TestClass"
        frame_info1.frame.f_locals = {"self": mock_self}
        
        # Mock frame with class method
        frame_info2 = Mock()
        frame_info2.function = "class_method"
        mock_cls = Mock()
        mock_cls.__name__ = "TestClass"
        frame_info2.frame.f_locals = {"cls": mock_cls}
        
        stack_frames = [frame_info1, frame_info2]
        
        result = _collect_valid_functions(stack_frames)
        
        expected = ["TestClass.instance_method", "TestClass.class_method"]
        self.assertEqual(result, expected)

    def test_collect_empty_stack(self):
        """Test collecting from empty stack frames."""
        result = _collect_valid_functions([])
        
        self.assertEqual(result, [])

    def test_collect_all_skipped_functions(self):
        """Test collecting when all functions should be skipped."""
        frame_info1 = Mock()
        frame_info1.function = "wrapper"
        frame_info1.frame.f_locals = {}
        
        frame_info2 = Mock()
        frame_info2.function = "__str__"
        frame_info2.frame.f_locals = {}
        
        stack_frames = [frame_info1, frame_info2]
        
        result = _collect_valid_functions(stack_frames)
        
        self.assertEqual(result, [])


class TestGetFunctionName(unittest.TestCase):
    """Test cases for get_function_name function."""

    def test_get_simple_function_name(self):
        """Test getting simple function name from stack."""
        def test_function():
            return get_function_name()
        
        result = test_function()
        
        # Should return the immediate caller (test_function)
        self.assertEqual(result, "test_function")

    def test_get_method_name(self):
        """Test getting method name with class context."""
        class TestClass:
            def test_method(self):
                return get_function_name()
        
        obj = TestClass()
        result = obj.test_method()
        
        self.assertEqual(result, "TestClass.test_method")

    def test_get_full_chain(self):
        """Test getting full function call chain."""
        def level_3():
            return get_function_name(full_chain=True)
        
        def level_2():
            return level_3()
        
        def level_1():
            return level_2()
        
        result = level_1()
        
        # Should contain the call chain
        self.assertIn("level_1", result)
        self.assertIn("level_2", result)
        self.assertIn("level_3", result)
        self.assertIn(" -> ", result)

    def test_get_function_name_with_max_depth(self):
        """Test limiting depth of function names."""
        def deep_level_4():
            return get_function_name(full_chain=True, max_depth=2)
        
        def deep_level_3():
            return deep_level_4()
        
        def deep_level_2():
            return deep_level_3()
        
        def deep_level_1():
            return deep_level_2()
        
        result = deep_level_1()
        
        # Should contain at most 2 function names
        function_names = result.split(" -> ")
        self.assertLessEqual(len(function_names), 2)

    def test_get_function_name_custom_separator(self):
        """Test using custom separator for function chain."""
        def func_b():
            return get_function_name(full_chain=True, separator=" | ")
        
        def func_a():
            return func_b()
        
        result = func_a()
        
        self.assertIn(" | ", result)
        self.assertNotIn(" -> ", result)

    @patch('adk_agui_middleware.tools.function_name.inspect.stack')
    def test_get_function_name_empty_stack(self, mock_stack):
        """Test handling empty or invalid stack."""
        mock_stack.return_value = []
        
        result = get_function_name()
        
        self.assertEqual(result, "unknown_function")

    @patch('adk_agui_middleware.tools.function_name._collect_valid_functions')
    def test_get_function_name_no_valid_functions(self, mock_collect):
        """Test when no valid functions are found."""
        mock_collect.return_value = []
        
        result = get_function_name()
        
        self.assertEqual(result, "unknown_function")

    def test_class_method_detection(self):
        """Test detection and formatting of class methods."""
        class TestClass:
            @classmethod
            def class_method(cls):
                return get_function_name()
        
        result = TestClass.class_method()
        
        self.assertEqual(result, "TestClass.class_method")

    def test_static_method_detection(self):
        """Test detection of static methods (should appear as regular functions)."""
        class TestClass:
            @staticmethod
            def static_method():
                return get_function_name()
        
        result = TestClass.static_method()
        
        # Static methods don't have self or cls, so should appear as function name only
        self.assertEqual(result, "static_method")

    def test_nested_function_calls(self):
        """Test handling of nested function calls."""
        def outer_function():
            def inner_function():
                return get_function_name(full_chain=True)
            return inner_function()
        
        result = outer_function()
        
        # Should include both outer and inner functions
        self.assertIn("outer_function", result)
        self.assertIn("inner_function", result)

    def test_function_name_with_lambda(self):
        """Test that lambda functions are properly skipped."""
        def regular_function():
            # Lambda should be skipped in the chain
            return (lambda: get_function_name())()
        
        result = regular_function()
        
        # Should return regular_function, skipping the lambda
        self.assertEqual(result, "regular_function")

    def test_max_depth_zero(self):
        """Test max_depth of 0."""
        def test_func():
            return get_function_name(full_chain=True, max_depth=0)
        
        result = test_func()
        
        # With max_depth=0, should return empty result or minimal result
        # This tests edge case handling
        self.assertIsInstance(result, str)

    def test_max_depth_one(self):
        """Test max_depth of 1."""
        def level_2():
            return get_function_name(full_chain=True, max_depth=1)
        
        def level_1():
            return level_2()
        
        result = level_1()
        
        # Should contain only one function name
        function_names = result.split(" -> ")
        self.assertEqual(len(function_names), 1)
        self.assertEqual(function_names[0], "level_2")


if __name__ == '__main__':
    unittest.main()