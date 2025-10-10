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
    async def dynamic_func(**kwargs: Any) -> T:
        return await cast(Callable[..., Coroutine[Any, Any, T]], func)(**kwargs)

    if param_list:
        dynamic_func.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
            [
                inspect.Parameter(param_name, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                for param_name in param_list
            ]
        )
    dynamic_func.__name__ = name
    dynamic_func.__doc__ = description
    return dynamic_func
