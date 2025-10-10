# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Dynamic function creation utility for generating callable with custom signatures."""

import inspect
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar, cast


P = ParamSpec("P")
T = TypeVar("T")


def create_function_with_params(
    func: Callable[P, Coroutine[Any, Any, T]],
    name: str,
    description: str,
    param_list: list[str],
) -> Callable[..., Coroutine[Any, Any, T]]:
    """Create a dynamic async function with custom signature and metadata.

    Generates a new async function that wraps the provided callable with a dynamically
    constructed signature based on the parameter list. This is particularly useful for
    creating tool functions that need to match specific schemas or signatures at runtime,
    such as frontend tools that are defined by client schemas.

    The created function preserves the original function's behavior while presenting
    a custom signature that can be inspected by tools, frameworks, and type checkers.

    Args:
        :param func: The original async callable to wrap
        :param name: Name to assign to the created function
        :param description: Docstring to assign to the created function
        :param param_list: List of parameter names for the function signature

    Returns:
        New async callable with customized name, docstring, and signature

    Note:
        The returned function accepts keyword arguments matching the param_list
        and forwards them to the wrapped function.
    """

    async def dynamic_func(**kwargs: Any) -> T:
        """Dynamically created wrapper function that forwards kwargs to the original callable."""
        return await cast(Callable[..., Coroutine[Any, Any, T]], func)(**kwargs)

    # Build custom signature from parameter names if provided
    if param_list:
        dynamic_func.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
            [
                inspect.Parameter(param_name, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                for param_name in param_list
            ]
        )
    # Set function metadata
    dynamic_func.__name__ = name
    dynamic_func.__doc__ = description
    return dynamic_func
