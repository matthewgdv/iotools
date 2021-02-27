from __future__ import annotations

import string
from typing import Any, Callable, Optional, TYPE_CHECKING

from subtypes import Dict

from .hierarchy import Hierarchy
from .argument import Argument
from .enums import RunMode

from iotools.misc import Validator, IoToolsConfig as Config

if TYPE_CHECKING:
    from .command import Command


# TODO: implement argument profiles
# TODO: improve dependent arguments


class ArgHandler:
    """
    A class that handles I/O by collecting arguments through the commandline, or generates a GUI to collect arguments if no commandline arguments are provided.
    The ArgHandler implicitly creates a folder structure in the directory of its script for storing the configuration of the previous run, and for providing output.
    """

    def __init__(self, name: str, desc: str = "", callback: Callable = None, run_mode: RunMode = RunMode.SMART, subtypes: bool = True, parent: ArgHandler = None, command: Command = None) -> None:
        self.name, self.desc, self.run_mode, self.callback, self.subtypes, self.parent = name, desc, run_mode, callback, subtypes, parent

        self.arguments: list[Argument] = []
        self.subhandlers: list[ArgHandler] = []
        self.command = command

        self.hierarchy: Optional[Hierarchy] = None

        self.remaining_letters = set(string.ascii_lowercase)
        self.remaining_letters.discard("h")

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def add_argument(self, argument: Argument) -> None:
        """Add a new Argument object to this ArgHandler. Passes on its arguments to the Argument constructor."""
        self.validate_name(argument.name)

        shortform = self.determine_shortform_alias(argument.name)
        if shortform is not None:
            argument.aliases = sorted([shortform, *argument.aliases], key=len)

        if isinstance(argument.validator, Validator):
            argument.validator.use_subtypes = self.subtypes

        self.arguments.append(argument)

    def add_subhandler(self, subhandler: ArgHandler) -> ArgHandler:
        self.validate_name(subhandler.name)

        self.subhandlers.append(subhandler)
        subhandler.parent = self

        return subhandler

    def process(self, *args: Any, **kwargs: Any) -> ArgHandler:
        """Collect input using this ArgHandler's 'run_mode' and return a CallableDict holding the parsed arguments, coerced to appropriate python types."""
        self.hierarchize()
        self.hierarchy = Hierarchy(root_handler=self)
        return self.hierarchy.choose_strategy(*args, **kwargs)

    def hierarchize(self, shared_namespace: Dict = None) -> None:
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

    def validate_name(self, name: str) -> None:
        if not name.isidentifier():
            raise ValueError(f"'{name}' is not a valid Python identifier.")

        if name in {entity.name for entity in [*self.arguments, *self.subhandlers]}:
            raise ValueError(f"Name '{name}' is already attached to this ArgHandler.")


# class Dependency:
#     class Mode(Enum):
#         ALL, ANY = "all", "any"
#
#     def __init__(self, *args: Argument, argument: Argument = None, mode: Dependency.Mode = Mode.ANY) -> None:
#         self.argument, self.arguments, self.mode = argument, list(args), self.Mode(mode).map_to({self.Mode.ALL: all, self.Mode.ANY: any})
#
#     def __repr__(self) -> str:
#         return f"{type(self).__name__}(argument={self.argument}, arguments=[{', '.join(arg.name for arg in self.arguments)}], mode={self.mode.__name__})"
#
#     def __str__(self) -> str:
#         return f"{', '.join(arg.name for arg in self.arguments)} [{self.mode.__name__}]"
#
#     def __bool__(self) -> bool:
#         return self.mode([bool(argument.value) for argument in self.arguments])
#
#     def bind(self, argument: Argument) -> Dependency:
#         self.argument = argument
#         return self
#
#     def validate(self) -> bool:
#         if self:
#             if self.argument.value is None:
#                 raise ValueError(f"""Must provide a value for argument '{self.argument}' if {self.mode.__name__} of: {", ".join(f"'{arg}'" for arg in self.arguments)} are truthy.""")
#         else:
#             if self.argument.value is not None:
#                 raise ValueError(f"""May not provide a value for argument '{self.argument}' unless {self.mode.__name__} of: {", ".join(f"'{arg}'" for arg in self.arguments)} are truthy.""")
#
#         return True
#
#
# class Nullability:
#     def __init__(self, truth: bool, argument: Argument) -> None:
#         self.truth, self.argument = truth, argument
#
#     def __repr__(self) -> str:
#         return f"{type(self).__name__}(truth={self.truth}, bool={bool(self)})"
#
#     def __str__(self) -> str:
#         return str(self.truth)
#
#     def __bool__(self) -> bool:
#         return self.truth if self.argument.dependency is None else True
