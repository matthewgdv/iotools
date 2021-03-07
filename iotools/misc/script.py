from __future__ import annotations

import pathlib
from contextlib import contextmanager
import functools
import traceback
from typing import Any, Callable, Type
import inspect

import appdirs

from maybe import Maybe
from subtypes import DateTime, Enum
from pathmagic import Dir, PathLike
from miscutils import ReprMixin, Timer, executed_within_user_tree

from .log import PrintLog


class Enums:
    class LoggingLevel(Enum):
        TEXT_ONLY = SERIALIZE_ON_FAILURE = ALWAYS_SERIALIZE = Enum.Auto()

    class FunctionType(Enum):
        INSTANCE = STATIC = CLASS = UNKNOWN = Enum.Auto()


class FunctionSpec(ReprMixin):
    def __init__(self, parent: Any, name: str, parent_reference: Any) -> None:
        self.class_, self.name, self.func = parent, f"{parent.__name__}.{name}", parent_reference if (ref_is_func := inspect.isfunction(parent_reference)) else parent_reference.__func__

        if ref_is_func:
            self.type = Enums.FunctionType.INSTANCE
        elif isinstance(parent_reference, staticmethod):
            self.type = Enums.FunctionType.STATIC
        elif isinstance(parent_reference, classmethod):
            self.type = Enums.FunctionType.CLASS
        else:
            self.type = Enums.FunctionType.UNKNOWN

        self.is_static = self.type == Enums.FunctionType.STATIC
        self.is_instance = self.type == Enums.FunctionType.INSTANCE
        self.is_class = self.type == Enums.FunctionType.CLASS
        self.is_bound = self.is_instance or self.is_class

    def wrap(self, func: Callable) -> Any:
        if self.is_instance:
            half_wrapped = func
        elif self.is_static:
            half_wrapped = staticmethod(func)
        elif self.is_class:
            half_wrapped = classmethod(func)
        else:
            raise ValueError(f"Don't know function type of {self}.")

        return functools.wraps(self.func)(half_wrapped)


class NestedPrintLog(PrintLog):
    def __init__(self, path: PathLike, active: bool = True, to_stream: bool = True, to_file: bool = True, indentation_token: str = "    ") -> None:
        super().__init__(path=path, active=active, to_stream=to_stream, to_file=to_file)
        self.indentation_token, self.indentation_level = indentation_token, 0

    def __enter__(self) -> NestedPrintLog:
        super().__enter__()
        return self

    def write(self, text: str, to_stream: bool = None, to_file: bool = None, add_newlines: int = 0) -> None:
        """Write the given text to this log's file and to sys.stdout, based on the 'to_console' and 'to_file' attributes set by the constructor. These attributes can be overriden by the arguments in this call."""
        if Maybe(to_stream).else_(self.to_stream):
            super().write(text, to_stream=True, to_file=False, add_newlines=add_newlines)

        if Maybe(to_file).else_(self.to_file):
            prefix = f"{DateTime.now().to_logformat()} - {self.indentation_token*self.indentation_level}"
            new_text = "\n".join(f"{prefix}{line}" if line else "" for line in text.split("\n"))
            super().write(text=new_text, to_stream=False, to_file=True, add_newlines=add_newlines)

    @contextmanager
    def indentation(self) -> NestedPrintLog:
        self.indentation_level += 1
        yield self
        self.indentation_level -= 1


class ScriptMeta(type):
    """The metaclass driving the Script class' magic behaviour."""

    def __init__(cls: Type[Script], name: str, bases: Any, namespace: dict) -> None:
        if bases:
            cls._recursively_wrap(item=cls)
            cls.__init__ = cls._init_wrapper(cls.__init__)

    def _recursively_wrap(cls: Type[Script], item: Any) -> None:
        for name, val in vars(item).items():
            if cls._is_valid_function_type(val) and (name == "__init__" or not (name.startswith("__") and name.endswith("__"))):
                setattr(item, name, cls._script_wrapper(FunctionSpec(parent=item, name=name, parent_reference=val)))

            elif inspect.isclass(val):
                cls._recursively_wrap(item=val)

    def _init_wrapper(cls: Type[Script], func: Callable) -> Callable:
        @functools.wraps(func)
        def init_wrapper(script: Script, *args: Any, **kwargs: Any) -> None:
            if pathlib.Path(cls.log_location).is_absolute():
                logs_dir = Dir(cls.log_location)
            else:
                appdata_root = appdirs.user_data_dir() if executed_within_user_tree() else appdirs.site_data_dir()
                logs_dir = Dir(appdata_root).new_dir("python").join_dir(cls.log_location)

            now = DateTime.now()
            log_path = logs_dir.new_dir(now.to_isoformat(time=False)).new_dir(cls.__name__).new_file(f"[{now.hour:02d}h {now.minute:02d}m {now.second:02d}s]", "txt")
            cls.log = log = NestedPrintLog(log_path)

            exception = None

            with log:
                try:
                    func(script, *args, **kwargs)
                except Exception as ex:
                    exception = ex
                    log.write(traceback.format_exc(), to_file=True, to_stream=False)
                finally:
                    PrintLog.write(log, f"\nAt point of exit, the final state of the script object was:\n{script}\n", to_file=True, to_stream=False)

            if cls.logging_level is Enums.LoggingLevel.ALWAYS_SERIALIZE or (cls.logging_level is Enums.LoggingLevel.SERIALIZE_ON_FAILURE and exception is not None):
                log.file.new_rename(cls.log.file.stem, "pkl").write(script)

            if exception is not None:
                raise exception

        return init_wrapper

    def _script_wrapper(cls: Type[Script], spec: FunctionSpec = None) -> Callable:
        def script_wrapper(*args: Any, **kwargs: Any) -> Any:
            instance = args[0] if spec.is_instance else None
            positional, keyword = ', '.join([repr(arg) for arg in args[1 if spec.is_bound else 0:]]), ', '.join([f'{name}={repr(val)}' for name, val in kwargs.items()])
            arguments = f"{positional}{f', ' if positional and keyword else ''}{keyword}"

            cls.log.write(f"{spec.name}({arguments}) starting...\n", to_file=True, to_stream=cls.verbose)

            with cls.log.indentation():
                with Timer() as timer:
                    ret = spec.func(*args, **kwargs)

            cls.log.write(f"{spec.name} finished in {timer.period} seconds, returning: {repr(ret)}.\n", to_file=True, to_stream=cls.verbose)

            return ret

        return spec.wrap(script_wrapper)

    def _is_valid_function_type(cls, candidate: Any) -> bool:
        return inspect.isfunction(candidate) or isinstance(candidate, (staticmethod, classmethod))


class Script(metaclass=ScriptMeta):
    """
    A Script class intended to be subclassed. Acquires a 'Script.name' attribute based on the stem of the file it is defined in.
    Performs detailed logging of the execution of the methods (in a call-_stack-aware, argument-aware, return-value-aware manner) defined within the class until the constructor returns.
    All console output will also be logged. The log can be accessed through the 'Script.log' attribute.
    Recommended usage is to write the high-level flow control of the script into the constructor, and call other methods from within it.
    """
    log: NestedPrintLog = None

    verbose = False
    logging_level = Enums.LoggingLevel.TEXT_ONLY
    log_location = "logs"

    def __init__(self, *args, **kwargs: Any) -> None:
        pass

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"
