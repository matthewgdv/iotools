from __future__ import annotations

import functools
import traceback
from typing import Dict, Any, cast, TypeVar, Callable
import inspect
import os

from maybe import Maybe
from subtypes import DateTime
from pathmagic import Dir, PathLike
from miscutils import Timer, executed_within_user_tree

from .log import PrintLog
from ..handler.iohandler import RunMode

# TODO: Investigate a solution to SqlLog output not being logged by the PrintLog

FuncSig = TypeVar("FuncSig", bound=Callable)


class NestedPrintLog(PrintLog):
    def __init__(self, path: PathLike, active: bool = True, to_console: bool = True, to_file: bool = True, indentation_token: str = "    ") -> None:
        super().__init__(path=path, active=active, to_console=to_console, to_file=to_file)
        self.indentation_token, self.indentation_level = indentation_token, 0

    def write(self, text: str, to_console: bool = None, to_file: bool = None, add_newlines: int = 0) -> None:
        """Write the given text to this log's file and to sys.stdout, based on the 'to_console' and 'to_file' attributes set by the constructor. These attributes can be overriden by the arguments in this call."""
        if Maybe(to_console).else_(self.to_console):
            super().write(text, to_console=True, to_file=False, add_newlines=add_newlines)

        if Maybe(to_file).else_(self.to_file):
            prefix = f"{DateTime.now().to_logformat()} - {self.indentation_token*self.indentation_level}"
            new_text = "\n".join(f"{prefix}{line}" if line else "" for line in text.split("\n"))
            super().write(text=new_text, to_console=False, to_file=True, add_newlines=add_newlines)


class ScriptProfiler:
    """A profiler decorator class used by the Script class."""

    def __init__(self, log: NestedPrintLog = None, verbose: bool = False) -> None:
        self.log, self.verbose = log, verbose

    def __call__(self, func: FuncSig = None) -> FuncSig:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            timer, to_console = Timer(), self.log.to_console

            positional, keyword = ', '.join([repr(arg) for arg in args[1:]]), ', '.join([f'{name}={repr(val)}' for name, val in kwargs.items()])
            arguments = f"{positional}{f', ' if positional and keyword else ''}{keyword}"
            func_name = f"{type(args[0]).__name__}.{func.__name__}"

            with self.log(to_console=self.verbose):
                print(f"{func_name}({arguments}) starting...")

            self.log.indentation_level += 1

            with self.log(to_console=True):
                ret = func(*args, **kwargs)

            self.log.indentation_level -= 1

            with self.log(to_console=self.verbose):
                has_repr = type(args[0]).__repr__ is not object.__repr__
                print(f"{func_name} finished in {timer} seconds, returning: {repr(ret)}.{f' State of the {type(args[0]).__name__} object is: {repr(args[0])}' if has_repr else ''}")

            self.log(to_console=to_console)

            return ret
        return cast(FuncSig, wrapper)


class ScriptMeta(type):
    """The metaclass driving the Script class' magic behaviour."""

    def __init__(cls, name: str, bases: Any, namespace: dict) -> None:
        profiler = ScriptProfiler(verbose=namespace.get("verbose", False))
        cls.recursively_wrap(item=cls, profiler=profiler)
        cls.__init__ = cls.constructor_wrapper(cls.__init__)

        cls.name, cls._profiler = os.path.splitext(os.path.basename(os.path.abspath(inspect.getfile(cls))))[0], profiler

    def recursively_wrap(cls, item: ScriptMeta, profiler: ScriptProfiler) -> None:
        for name, val in vars(item).items():
            if inspect.isfunction(val) and (name == "__init__" or not (name.startswith("__") and name.endswith("__"))):
                setattr(item, name, profiler(val))

            elif inspect.isclass(val):
                cls.recursively_wrap(item=val, profiler=profiler)

    def constructor_wrapper(cls, func: FuncSig) -> FuncSig:
        @functools.wraps(func)
        def wrapper(self: Script, **arguments: Any) -> None:
            self.arguments = arguments

            now = DateTime.now()
            logs_dir = (Dir.from_home() if executed_within_user_tree() else Dir.from_root()).new_dir("Python").new_dir("logs")
            log_path = logs_dir.new_dir(now.to_isoformat(time=False)).new_dir(self.name).new_file(f"[{now.hour}h {now.minute}m {now.second}s {now.microsecond}ms]", "txt")
            self.log = NestedPrintLog(log_path)

            self._profiler.log = self.log

            exception = None

            try:
                func(self)
            except Exception as ex:
                exception = ex
                self.log.write(traceback.format_exc(), to_console=False)

            if self.serialize:
                self.log.file.new_rename(self.log.file.stem, "pkl").content = self

            if exception is not None:
                raise exception

        return cast(FuncSig, wrapper)


class Script(metaclass=ScriptMeta):
    """
    A Script class intended to be subclassed. Acquires a 'Script.name' attribute based on the stem of the file it is defined in.
    Performs detailed logging of the execution of the methods (in a call-stack-aware, argument-aware, return-value-aware manner) defined within the class until the contructor returns.
    All console output will also be logged. The log can be accessed through the 'Script.log' attribute.
    Recommended usage is to write the high-level flow control of the script into the constructor, and call other methods from within it.
    Upon exiting the constructor, the script object itself will be serialized using the pickle protocol.
    """
    name: str
    arguments: Dict[str, Any]
    log: NestedPrintLog

    run_mode = RunMode.SMART
    verbose = serialize = False

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"
