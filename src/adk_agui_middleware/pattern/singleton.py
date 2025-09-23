# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Singleton design pattern implementation using metaclass."""

from typing import Any


class Singleton(type):
    """Metaclass that implements the Singleton design pattern.

    Ensures that only one instance of a class can exist by caching instances
    and returning the same instance for subsequent instantiation attempts.
    """

    _instances: dict[Any, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Create or return the singleton instance of the class.

        Args:
            :param *args: Positional arguments for class instantiation
            :param **kwargs: Keyword arguments for class instantiation

        Returns:
            The singleton instance of the class
        """
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
