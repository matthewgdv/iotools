from __future__ import annotations

import functools
import traceback
from typing import Dict, Any, Type, cast, TypeVar, Callable
import inspect
import os

from maybe import Maybe
from subtypes import DateTime
from pathmagic import Dir
from miscutils import Counter, Timer, executed_within_user_tree

from .log import PrintLog
from ..handler.iohandler import RunMode

FuncSig = TypeVar("FuncSig", bound=Callable)


class ScriptProfiler:
    """A profiler decorator class used by the Script class."""

    def __init__(self, log: PrintLog = None, verbose: bool = False) -> None:
        self.log, self.verbose, self.stack = log, verbose, Counter()

    def __call__(self, func: FuncSig = None) -> FuncSig:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            timer, to_console = Timer(), self.log.to_console

            positional, keyword = ', '.join([repr(arg) for arg in args[1:]]), ', '.join([f'{name}={repr(val)}' for name, val in kwargs.items()])
            arguments = f"{positional}{f', ' if positional and keyword else ''}{keyword}"
            func_name = f"{type(args[0]).__name__}.{func.__name__}"

            with self.log(to_console=self.verbose):
                print(f"{self.prefix}{func_name}({arguments}) starting...")

            self.stack.increment()

            with self.log(to_console=True):
                ret = func(*args, **kwargs)

            self.stack.decrement()

            with self.log(to_console=self.verbose):
                has_repr = type(args[0]).__repr__ is not object.__repr__
                print(f"{self.prefix}{func_name} finished in {timer} seconds, returning: {repr(ret)}.{f' State of the {type(args[0]).__name__} object is: {repr(args[0])}' if has_repr else ''}")

            self.log(to_console=to_console)

            return ret
        return cast(FuncSig, wrapper)

    @property
    def prefix(self) -> str:
        return f"{DateTime.now().logformat()} - {'    '*int(Maybe(self.stack).else_(0))}"


class ScriptMeta(type):
    """The metaclass driving the Script class' magic behaviour."""

    def __new__(mcs, name: str, bases: Any, namespace: dict) -> Type[Script]:
        def recursively_wrap(cls: Script, profiler: ScriptProfiler) -> None:
            for name, val in vars(cls).items():
                if inspect.isfunction(val) and (name == "__init__" or not (name.startswith("__") and name.endswith("__"))):
                    setattr(cls, name, profiler(val))

                elif inspect.isclass(val):
                    recursively_wrap(cls=val, profiler=profiler)

        cls: Type[Script] = type.__new__(mcs, name, bases, namespace)

        if not name == "Script":
            profiler = ScriptProfiler(verbose=namespace.get("verbose", False))
            recursively_wrap(cls=cls, profiler=profiler)
            cls.__init__ = mcs.constructor_wrapper(cls.__init__)

            cls.name, cls._profiler = os.path.splitext(os.path.basename(os.path.abspath(inspect.getfile(cls))))[0], profiler

        return cls

    def constructor_wrapper(func: FuncSig) -> FuncSig:
        @functools.wraps(func)
        def wrapper(self: Script, **arguments: Any) -> None:
            self.arguments = arguments

            now = DateTime.now()
            logs_dir = (Dir.from_home() if executed_within_user_tree() else Dir.from_root()).new_dir("Python").new_dir("logs")
            log_path = logs_dir.new_dir(now.isoformat_date()).new_dir(self.name).new_file(f"[{now.hour}h {now.minute}m {now.second}s {now.microsecond}ms]", "txt")
            self.log = PrintLog(log_path)

            self._profiler.log = self.log

            exception = None

            try:
                func(self)
            except Exception as ex:
                exception = ex
                self.log.write(traceback.format_exc(), to_console=False)

            if self.serialize:
                self.log.file.new_rename(self.log.file.stem, "pkl").contents = self

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
    log: PrintLog

    run_mode = RunMode.SMART
    verbose = serialize = False

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"
