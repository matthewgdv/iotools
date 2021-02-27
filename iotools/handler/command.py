from __future__ import annotations

from typing import Any, Callable, Type

from miscutils import ReprMixin

from .arghandler import ArgHandler
from .argument import Argument
from .enums import RunMode


class CommandMeta(type):
    stack: list[Command] = []

    def __init__(cls, name: str, bases: tuple, namespace: dict) -> None:
        cls._arguments_: dict[str, Argument] = {}
        cls._subcommands_: dict[str, Type[Command]] = {}

        for name, val in namespace.items():
            if isinstance(val, CommandMeta) and issubclass(val, Command):
                cls._subcommands_[name] = val
            elif isinstance(val, Argument):
                cls._arguments_[name] = val
                if not val.name:
                    val.name = name


class Command(ReprMixin, metaclass=CommandMeta):
    def __init__(self, name: str = None, desc: str = None, callback: Callable = None, run_mode: RunMode = RunMode.SMART, subtypes: bool = True) -> None:
        parent = type(self).stack[-1] if type(self).stack else None
        self._handler_ = ArgHandler(name=name or type(self).__name__, desc=desc or self.__doc__, callback=callback or self._callback_,
                                    run_mode=run_mode, subtypes=subtypes,
                                    parent=parent, command=self)

        for name, argument in self._arguments_.items():
            self._handler_.add_argument(argument)

        for name, command in self._subcommands_.items():
            self._handler_.add_subhandler(command()._handler_)

    def __call__(self, *args: Any, **kwargs) -> Command:
        handler = self._handler_.process(*args, **kwargs)
        return handler.command

    def __enter__(self) -> Command:
        type(self).stack.append(self)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        type(self).stack.pop()

    def __getitem__(self, item: Any) -> Command:
        return self._handler_.shared_namespace[item]

    def __setitem__(self, key: Any, value: Any) -> None:
        self._handler_.shared_namespace[key] = value

    def __getattr__(self, item: str) -> Any:
        return super().__getattribute__(item)

    def _callback_(self) -> Any:
        pass
