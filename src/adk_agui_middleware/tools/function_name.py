# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Function name extraction utilities for debugging and logging."""

import inspect
from typing import Any


def _should_skip_function(function_name: str) -> bool:
    """Determine if a function should be skipped from the call chain.

    Filters out logging functions, wrappers, and most dunder methods
    to provide cleaner function name chains for debugging. This helps
    focus on business logic functions rather than infrastructure code.

    Args:
        :param function_name: Name of the function to evaluate

    Returns:
        True if the function should be skipped, False otherwise
    """
    # Functions to always skip (logging, wrappers, etc.)
    default_skip = {
        "get_function_name",
        "_record_raw_data_log",
        "_create_and_log_message",
        "wrapper",
        "__call__",
        "<lambda>",
        "<module>",
        "<listcomp>",
        "<dictcomp>",
        "<setcomp>",
        "log_call",
        "trace",
        "debug",
    }

    # Special dunder methods that are meaningful to include
    default_include_special = {
        "__init__",
        "__new__",
        "__enter__",
        "__exit__",
    }

    if function_name in default_skip:
        return True

    # Skip most dunder methods except meaningful ones
    return (
        function_name.startswith("__")
        and function_name.endswith("__")
        and function_name not in default_include_special
    )


def _format_function_name(function_name: str, frame_locals: dict[str, Any]) -> str:
    """Format function name with class context if available.

    Examines frame locals to determine if the function is a method,
    class method, or standalone function and formats accordingly.
    This provides better context for debugging and logging.

    Args:
        :param function_name: Base function name
        :param frame_locals: Local variables from the function's frame

    Returns:
        Formatted function name with class context (e.g., "ClassName.method_name")
    """
    # Instance method: has 'self' parameter
    if "self" in frame_locals:
        class_name = frame_locals["self"].__class__.__name__
        return f"{class_name}.{function_name}"

    # Class method: has 'cls' parameter
    if "cls" in frame_locals:
        class_name = frame_locals["cls"].__name__
        return f"{class_name}.{function_name}"

    # Standalone function
    return function_name


def _collect_valid_functions(stack_frames: list[Any]) -> list[str]:
    """Collect and format valid function names from stack frames.

    Processes the call stack to extract meaningful function names,
    filtering out internal functions and formatting with class context.
    This creates a clean representation of the execution path.

    Args:
        :param stack_frames: List of frame info objects from inspect.stack()

    Returns:
        List of formatted function names in call order
    """
    valid_functions = []
    for frame_info in stack_frames:
        function_name = frame_info.function

        # Skip functions that shouldn't be included in the chain
        if _should_skip_function(function_name):
            continue

        # Format with class context if available
        formatted_name = _format_function_name(function_name, frame_info.frame.f_locals)
        valid_functions.append(formatted_name)

    return valid_functions


def extract_caller_name(
    full_chain: bool = False,
    separator: str = " -> ",
    max_depth: int | None = None,
) -> str:
    """Extract function name or call chain from the current execution stack.

    Analyzes the call stack to provide meaningful function names for logging
    and debugging, with options for full call chains and depth limiting.
    This is particularly useful for structured logging and error reporting.

    Args:
        :param full_chain: If True, return full call chain; if False, return just caller
        :param separator: String used to separate function names in full chain
        :param max_depth: Maximum number of functions to include (None for unlimited)

    Returns:
        Function name or call chain string, "unknown_function" if none found

    Examples:
        extract_caller_name() -> "MyClass.my_method"
        extract_caller_name(full_chain=True) -> "main -> MyClass.my_method -> helper"
        extract_caller_name(max_depth=2) -> "MyClass.my_method"
    """
    # Get the current call stack
    stack_frames = inspect.stack()

    # Filter and format valid function names
    valid_functions = _collect_valid_functions(stack_frames)

    if not valid_functions:
        return "unknown_function"

    # Limit depth if specified
    if max_depth is not None:
        valid_functions = valid_functions[:max_depth]

    # Return just the immediate caller or full chain
    if not full_chain:
        return valid_functions[0]

    # For full chain, reverse to show call order (deepest to shallowest)
    valid_functions.reverse()
    return separator.join(valid_functions)
