from __future__ import annotations

import pathlib
from types import MethodType
from typing import Any, Callable, Type
import inspect

from wrapt import decorator

from subtypes import DateTime, Enum
from pathmagic import Dir
from miscutils import ReprMixin, Timer, executed_within_user_tree

import iotools
from iotools import IndentationPrintLog


class Enums:
    class LoggingLevel(Enum):
        TEXT_ONLY = SERIALIZE_ON_FAILURE = ALWAYS_SERIALIZE = Enum.Auto()


class ScriptMeta(type):
    """The metaclass driving the Script class' magic behaviour."""

    def __init__(cls: Type[Script], name: str, bases: Any, namespace: dict) -> None:
        if bases:
            cls._recursively_wrap(item=cls)
            cls.__init__ = cls._init_wrapper()(cls.__init__)

    def _recursively_wrap(cls: Type[Script], item: Any) -> None:
        for name, val in vars(item).items():
            if cls._is_valid_function_type(val) and (name == "__init__" or not (name.startswith("__") and name.endswith("__"))):
                setattr(item, name, cls._script_wrapper()(val))

            elif inspect.isclass(val):
                cls._recursively_wrap(item=val)

    def _init_wrapper(cls: Type[Script]) -> Callable:
        @decorator
        def init_wrapper(func: Callable, script: Any, args: Any, kwargs: Any) -> None:
            if pathlib.Path(cls.log_location).is_absolute():
                logs_dir = Dir(cls.log_location)
            else:
                logs_dir = Dir.from_appdata(systemwide=not executed_within_user_tree()).new_dir("python").new_dir("logs").join_dir(cls.log_location)

            now = DateTime.now()
            log_path = logs_dir.new_dir(now.date().to_isoformat()).new_dir(cls.__name__).new_file(f"[{now.hour:02d}h {now.minute:02d}m {now.second:02d}s]", "log")
            cls.log = log = IndentationPrintLog(log_path)

            with log:
                try:
                    func(*args, **kwargs)
                except Exception as ex:
                    exception = ex
                else:
                    exception = None

                with log.no_indentation():
                    log.delimiter_lesser()
                    log.debug(f"At point of exit, the final state of the script object was:")
                    log.debug(str(script))

            if cls.logging_level is Enums.LoggingLevel.ALWAYS_SERIALIZE or exception is not None and cls.logging_level is Enums.LoggingLevel.SERIALIZE_ON_FAILURE:
                log.file.new_rename(cls.log.file.stem, "pkl").write(script)

            if exception is not None:
                raise exception

        return init_wrapper

    def _script_wrapper(cls: Type[Script]) -> Callable:
        @decorator
        def script_wrapper(func: MethodType, instance: Any, args: Any, kwargs: Any) -> Any:
            positional = ', '.join(([] if instance is None else ["self"]) + [repr(arg) for arg in args])
            keyword = ', '.join([f'{name}={repr(val)}' for name, val in kwargs.items()])
            arguments = f"{positional}{f', ' if positional and keyword else ''}{keyword}"

            func_name = func.__name__ if not hasattr(func, "__self__") else f"{type(func.__self__).__name__}.{func.__name__}"

            cls.log.debug(f"{func_name}({arguments})")

            with cls.log.indentation(), Timer() as timer:
                ret = func(*args, **kwargs)

            cls.log.debug(f"{func_name} [{timer.period:.3f}s] -> {repr(ret)}")

            return ret

        return script_wrapper

    def _is_valid_function_type(cls, candidate: Any) -> bool:
        return inspect.isfunction(candidate) or isinstance(candidate, (staticmethod, classmethod))


class Script(ReprMixin, metaclass=ScriptMeta):
    """
    A Script class intended to be subclassed. Acquires a 'Script.name' attribute based on the stem of the file it is defined in.
    Performs detailed logging of the execution of the methods (in a call-_stack-aware, argument-aware, return-value-aware manner) defined within the class until the constructor returns.
    All console output will also be logged. The log can be accessed through the 'Script.log' attribute.
    Recommended usage is to write the high-level flow control of the script into the constructor, and call other methods from within it.
    """
    log: IndentationPrintLog = None

    verbose = False
    logging_level = Enums.LoggingLevel.TEXT_ONLY
    log_location = f"{iotools.__name__}/misc"

    def __init__(self, *args, **kwargs: Any) -> None:
        pass

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"
