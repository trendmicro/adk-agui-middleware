import inspect


def _should_skip_function(function_name: str) -> bool:
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
    default_include_special = {
        "__init__",
        "__new__",
        "__enter__",
        "__exit__",
    }
    if function_name in default_skip:
        return True
    return (
        function_name.startswith("__")
        and function_name.endswith("__")
        and function_name not in default_include_special
    )


def _format_function_name(function_name: str, frame_locals: dict) -> str:
    if "self" in frame_locals:
        class_name = frame_locals["self"].__class__.__name__
        return f"{class_name}.{function_name}"
    if "cls" in frame_locals:
        class_name = frame_locals["cls"].__name__
        return f"{class_name}.{function_name}"
    return function_name


def _collect_valid_functions(stack_frames: list) -> list[str]:
    valid_functions = []
    for frame_info in stack_frames:
        function_name = frame_info.function
        if _should_skip_function(function_name):
            continue
        formatted_name = _format_function_name(function_name, frame_info.frame.f_locals)
        valid_functions.append(formatted_name)
    return valid_functions


def get_function_name(
    full_chain: bool = False,
    separator: str = " -> ",
    max_depth: int | None = None,
) -> str:
    stack_frames = inspect.stack()
    valid_functions = _collect_valid_functions(stack_frames)
    if not valid_functions:
        return "unknown_function"
    if max_depth is not None:
        valid_functions = valid_functions[:max_depth]
    if not full_chain:
        return valid_functions[0]
    valid_functions.reverse()
    return separator.join(valid_functions)
