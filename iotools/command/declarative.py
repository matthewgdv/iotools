from __future__ import annotations

from typing import Any, Callable, Type, Union

from miscutils import ReprMixin, issubclass_safe

from .argument import Argument
from .enums import RunMode
from .stack import Stack
from .handler import CommandHandler, GroupHandler


class DeclarativeMeta(type):
    _initialized_ = False

    def __init__(cls, name: str, bases: tuple, namespace: dict) -> None:
        cls._arguments_: dict[str, Argument] = {}
        cls._groups_: dict[str, Type[Group]] = {}

        if cls._initialized_:
            for name, val in namespace.items():
                if isinstance(val, Argument):
                    type(cls)._handle_argument_(cls, name=name, argument=val)
                elif issubclass_safe(val, Command):
                    type(cls)._handle_command_(cls, name=name, command=val)
                elif issubclass_safe(val, Group):
                    type(cls)._handle_group_(cls, name=name, group=val)

    def _handle_argument_(cls, name: str, argument: Argument) -> None:
        if argument.name:
            raise RuntimeError(f"Cannot provide an argument name explicitly when defining a {Command.__name__} declaratively: ({argument.name}).")

        argument.name = name
        cls._arguments_[name] = argument

    def _handle_group_(cls, name: str, group: Type[Group]) -> None:
        cls._groups_[name] = group

    def _handle_command_(cls, name: str, command: Type[Command]) -> None:
        raise NotImplementedError


class CommandMeta(DeclarativeMeta):
    def __init__(cls, name: str, bases: tuple, namespace: dict) -> None:
        cls._subcommands_: dict[str, Type[Command]] = {}
        super().__init__(name=name, bases=bases, namespace=namespace)

    def _handle_command_(cls, name: str, command: Type[Command]) -> None:
        cls._subcommands_[name] = command


class Command(ReprMixin, metaclass=CommandMeta):
    def __init__(self, name: str = None, desc: str = None, callback: Callable = None, run_mode: RunMode = RunMode.SMART) -> None:
        if Stack.groups:
            raise RuntimeError(f"Cannot instanciate a new command within the context of an argument group: {Stack.groups[-1]}.")

        self._handler_ = CommandHandler(name=name or type(self).__name__, desc=desc or self.__doc__, callback=callback or self._callback_, run_mode=run_mode,
                                        parent=Stack.commands[-1] if Stack.commands else None, command=self)

        for name, argument in type(self)._arguments_.items():
            setattr(self, name, argument)
            self._handler_.add_argument(argument)

        for name, group in type(self)._groups_.items():
            setattr(self, name, group_instance := group(parent=self))
            self._handler_.add_group(group_instance._handler_)

        for name, command in type(self)._subcommands_.items():
            setattr(self, name, command_instance := command())
            self._handler_.add_subhandler(command_instance._handler_)

    def __call__(self, *args: Any, **kwargs) -> Command:
        handler = self._handler_.process(*args, **kwargs)
        return handler.command

    def __enter__(self) -> Command:
        Stack.commands.append(self)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        Stack.commands.pop()

    def __getitem__(self, item: Any) -> Command:
        return self._handler_.shared_namespace[item]

    def __setitem__(self, key: Any, value: Any) -> None:
        self._handler_.shared_namespace[key] = value

    def __getattr__(self, item: str) -> Union[Argument, Group, Command]:
        return super().__getattribute__(item)

    def _callback_(self) -> Any:
        pass


class GroupMeta(DeclarativeMeta):
    def _handle_command_(cls, name: str, command: Type[Command]) -> None:
        raise RuntimeError(f"Cannot nest a {Command.__name__} ({command}) within a {Group.__name__} ({cls}).")


class Group(ReprMixin, metaclass=GroupMeta):
    def __init__(self, name: str = None, parent: Union[Command, Group] = None) -> None:
        parent = (
            parent._handler_ if parent is not None else (
                Stack.groups[-1] if Stack.groups else (
                    Stack.commands[-1] if Stack.commands else None
                )
            )
        )
        self._handler_ = GroupHandler(name=name or type(self).__name__, parent=parent, group=self)

        for name, argument in type(self)._arguments_.items():
            setattr(self, name, argument)
            self._handler_.add_argument(argument)

        for name, group in type(self)._groups_.items():
            setattr(self, name, group_instance := group(parent=self))
            self._handler_.add_group(group_instance._handler_)

    def __enter__(self) -> Group:
        Stack.groups.append(self)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        Stack.groups.pop()

    def __getattr__(self, item: str) -> Union[Argument, Group, Command]:
        return super().__getattribute__(item)


class InclusiveGroup(Group):
    pass


class ExclusiveGroup(Group):
    pass


class ArgumentGroup:
    Inclusive = InclusiveGroup
    Exclusive = ExclusiveGroup


DeclarativeMeta._initialized_ = True
