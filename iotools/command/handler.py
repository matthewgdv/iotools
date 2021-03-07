from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

import string

from subtypes import Dict

from iotools.misc import IoToolsConfig as Config

from .argument import Argument
from .enums import RunMode
from .hierarchy import Hierarchy

if TYPE_CHECKING:
    from .declarative import Command, Group


class Handler:
    def __init__(self, name: str, parent: Handler = None) -> None:
        self.name, self.parent = name, parent

        self.arguments: list[Argument] = []
        self.groups: list[GroupHandler] = []
        self.names: set[str] = set()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __bool__(self) -> bool:
        return all([*self.arguments, *self.groups])

    def add_argument(self, argument: Argument) -> None:
        """Add a new Argument object to this CommandHandler. Passes on its arguments to the Argument constructor."""
        self.register_name(argument.name)
        self.arguments.append(argument)

    def add_group(self, group: GroupHandler) -> None:
        self.register_name(group.name)
        self.groups.append(group)
        group.parent = self

    def register_name(self, name: str) -> None:
        if not name.isidentifier():
            raise ValueError(f"Name '{name}' is not a valid Python identifier.")

        if name in self.names:
            raise ValueError(f"Name '{name}' is already attached to this {type(self).__name__}.")

        self.names.add(name)


class CommandHandler(Handler):
    """
    A class that handles I/O by collecting arguments through the commandline, or generates a GUI to collect arguments if no commandline arguments are provided.
    The CommandHandler implicitly creates a folder structure in the directory of its script for storing the configuration of the previous run, and for providing output.
    """
    parent: CommandHandler

    def __init__(self, name: str, desc: str = "", callback: Callable = None, run_mode: RunMode = RunMode.SMART, subtypes: bool = True, parent: CommandHandler = None, command: Command = None) -> None:
        super().__init__(name=name, parent=parent)
        self.desc, self.run_mode, self.callback = desc, run_mode, callback

        self.subhandlers: list[CommandHandler] = []
        self.command = command

        self.hierarchy: Optional[Hierarchy] = None

        self.remaining_letters = set(string.ascii_lowercase)
        self.remaining_letters.discard("h")

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def add_argument(self, argument: Argument) -> None:
        """Add a new Argument object to this CommandHandler. Passes on its arguments to the Argument constructor."""
        super().add_argument(argument)

        if shortform := self.determine_shortform_alias(argument.name):
            argument.aliases.append(shortform)

    def add_subhandler(self, subhandler: CommandHandler) -> None:
        self.register_name(subhandler.name)
        self.subhandlers.append(subhandler)
        subhandler.parent = self

    def process(self, *args: Any, **kwargs: Any) -> CommandHandler:
        """Collect input using this CommandHandler's 'run_mode' and return a CallableDict holding the parsed arguments, coerced to appropriate python types."""
        self.pre_validate()
        self.hierarchize()
        self.hierarchy = Hierarchy(root_handler=self)
        return self.hierarchy.choose_strategy(*args, **kwargs)

    def pre_validate(self) -> None:
        for group in self.groups:
            group.pre_validate()

        for child in self.subhandlers:
            child.pre_validate()

    def post_validate(self) -> None:
        for group in self.groups:
            group.post_validate()

    def hierarchize(self) -> None:
        self.configure()
        for child in self.subhandlers:
            child.hierarchize()

    def configure(self) -> None:
        if self.parent:
            self.config = self.parent.config
            self.root = self.parent.root
            self.folder = self.parent.folder.new_dir(self.name)

            self.shared_namespace = self.parent.shared_namespace
        else:
            self.config = Config()
            self.root = self.folder = self.config.folder.new_dir(self.name)

            self.shared_namespace = Dict()

        self.latest = self.folder.new_file("latest", "pkl")

    def save_latest_input_config(self, namespace: Dict) -> None:
        self.latest.write(namespace)

    def load_latest_input_config(self) -> dict[str, Any]:
        if self.latest:
            return self.latest.read()
        else:
            print(f"No prior configuration found for '{self.name}'")

    def determine_shortform_alias(self, name: str) -> str:
        for char in name:
            if char.isalnum():
                letter = char.lower()
                if letter in self.remaining_letters:
                    self.remaining_letters.remove(letter)
                    return letter


class GroupHandler(Handler):
    def __init__(self, name: str, parent: Handler = None, group: Group = None) -> None:
        super().__init__(name=name, parent=parent)
        self.group = group

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __bool__(self) -> bool:
        from .declarative import ArgumentGroup

        if isinstance(self.group, ArgumentGroup.Exclusive):
            return len([*filter(None, [*self.arguments, *self.groups])]) <= 1

        return super().__bool__()

    def add_argument(self, argument: Argument) -> None:
        """Add a new Argument object to this CommandHandler. Passes on its arguments to the Argument constructor."""
        super().add_argument(argument)

        parent = self.parent
        while not isinstance(parent, CommandHandler):
            parent = parent.parent

        parent.add_argument(argument)

    def pre_validate(self) -> None:
        from .declarative import ArgumentGroup

        if isinstance(self.group, ArgumentGroup.Inclusive):
            if all([*self.arguments, *self.groups]):
                raise RuntimeError(f"The {ArgumentGroup.Inclusive.__name__} {self.group._handler_.name} is valid in all circumstances due to argument nullability and defaults.")
        elif isinstance(self.group, ArgumentGroup.Exclusive):
            if any([*self.arguments, *self.groups]):
                truthiness = {item: bool(item) for item in [*self.arguments, *self.groups]}
                raise RuntimeError(f"The {ArgumentGroup.Exclusive.__name__} {self.group._handler_.name} contains at least one argument or group that is always valid due to argument nullability and defaults.")

    def post_validate(self) -> None:
        from .declarative import ArgumentGroup

        if not self:
            if isinstance(self.group, ArgumentGroup.Inclusive):
                for argument in self.arguments:
                    if not argument:
                        raise RuntimeError(f"Argument {argument.name} of {ArgumentGroup.Inclusive.__name__} {self.group._handler_.name} was not provided.")

                for group in self.groups:
                    if not group:
                        group.post_validate()
            elif isinstance(self.group, ArgumentGroup.Exclusive):
                provided_items = [item.name for item in (*self.arguments, *self.groups) if item]
                raise RuntimeError(f"At most one argument or argument group of {ArgumentGroup.Exclusive.__name__} {self.group._handler_.name} can be provided. Provided:\n\n{', '.join(provided_items)}")
