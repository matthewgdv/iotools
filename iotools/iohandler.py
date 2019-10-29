from __future__ import annotations

import string
import sys
from typing import Any, Callable, Dict, List, Union

from maybe import Maybe
from subtypes import Enum, AutoEnum, Frame
from miscutils import NameSpaceDict, lazy_property, is_running_in_ipython
import miscutils

from .widget import WidgetHandler
from .validator import Validate, Condition, StringValidator, IntegerValidator, FloatValidator, DecimalValidator, BoolValidator, ListValidator, DictionaryValidator, PathValidator, FileValidator, DirValidator, DateTimeValidator, UnknownTypeValidator
from .synchronizer import Synchronizer
import iotools

# TODO: implement argument profiles
# TODO: implement dependent arguments


class RunMode(AutoEnum):
    """An Enum of the various run modes an IOHandler accepts."""
    SMART, COMMANDLINE, GUI, PROGRAMMATIC  # noqa


class ArgType(Enum):
    """An Enum of the various argument types an IOHandler understands."""
    String, Integer, Float, Boolean, List, Dict = StringValidator, IntegerValidator, FloatValidator, BoolValidator, ListValidator, DictionaryValidator
    Path, File, Dir = PathValidator, FileValidator, DirValidator
    DateTime, Decimal, Frame = DateTimeValidator, DecimalValidator, UnknownTypeValidator(Frame)


class Config(miscutils.Config):
    """A config class granting access to an os-specific appdata directory for use by this application."""
    app_name = iotools.__name__


class IOHandler:
    """
    A class that handles I/O by collecting arguments through the commandline, or generates a GUI to collect arguments if no commandline arguments are provided.
    The IOHandler implicitly creates a folder structure in the directory of its script for storing the configuration of the previous run, and for providing output.
    """

    stack: List[IOHandler] = []

    def __init__(self, app_name: str, app_desc: str = "", name: str = "main", run_mode: str = RunMode.SMART, parent: IOHandler = None) -> None:
        self.app_name, self.app_desc, self.name, self.run_mode, self.parent, self.config = app_name, app_desc, name, run_mode, parent, Config()

        self.arguments: Dict[str, Argument] = {}
        self.subcommands: Dict[str, IOHandler] = {}
        self.sync: Synchronizer = None

        self._remaining_letters = set(string.ascii_lowercase)
        self._remaining_letters.discard("h")

        self._dir = (self.config.appdata.new_dir(self.app_name) if self.parent is None else self.parent._dir).new_dir(self.name)
        workfolder = self._dir.new_dir("__io__")
        self.outfile, self.outdir, self._latest = workfolder.new_file("output", "txt"), workfolder.new_dir("output"), workfolder.new_file("latest", "pkl")

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __enter__(self) -> IOHandler:
        self.stack.append(self)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        self.stack.pop()

    def add_argument(self, argument: Argument) -> None:
        """Add a new Argument object to this IOHandler. Passes on its arguments to the Argument constructor."""
        self._validate_arg_name(argument.name)
        shortform = self._determine_shortform_alias(argument.name)

        if shortform is not None:
            argument.aliases = sorted([shortform, *argument.aliases], key=len)

        self.arguments[argument.name] = argument

    def add_subcommand(self, name: str) -> IOHandler:
        """Add a new subcommand to this IOHandler, which is itself an IOHandler. The subcommand will process its own set of arguments when the given verb is used."""
        subcommand = IOHandler(app_name=self.app_name, app_desc=self.app_desc, name=name, run_mode=self.run_mode, parent=self)
        self.subcommands[name] = subcommand
        return subcommand

    def process(self, arguments: Dict[str, Any] = None, subcommand: str = None) -> NameSpaceDict:
        """Collect input using this IOHandler's 'run_mode' and return a NameSpaceDict holding the parsed arguments, coerced to appropriate python types."""
        self.sync = Synchronizer(root_handler=self)

        if self.run_mode == RunMode.COMMANDLINE:
            namespace = self.sync.run_from_commandline()
        elif self.run_mode == RunMode.GUI:
            namespace = self.sync.run_as_gui(arguments=arguments, subcommand=subcommand)
        elif self.run_mode == RunMode.PROGRAMMATIC:
            namespace = self.sync.run_programatically(arguments=arguments, subcommand=subcommand)
        elif self.run_mode == RunMode.SMART:
            if subcommand or arguments:
                namespace = self.sync.run_programatically(arguments=arguments, subcommand=subcommand)
            else:
                if not sys.argv[1:] or is_running_in_ipython():
                    namespace = self.sync.run_as_gui(arguments=arguments, subcommand=subcommand)
                else:
                    namespace = self.sync.run_from_commandline()
        else:
            RunMode.raise_if_not_a_member(self.run_mode)

        self._save_latest_input_config(namespace=namespace)

        return namespace

    def show_output(self, outfile: bool = True, outdir: bool = True) -> None:
        """Show the output file and/or folder belonging to this IOHandler."""
        if outfile:
            self.outfile.start()
        if outdir:
            self.outdir.start()

    def clear_output(self, outfile: bool = True, outdir: bool = True) -> None:
        """Clear the output file and/or folder belonging to this IOHandler."""
        if outfile:
            self.outfile.contents = ""

        if outdir:
            self.outdir.clear()

    def _save_latest_input_config(self, namespace: NameSpaceDict) -> None:
        self._latest.contents = namespace

    def _load_latest_input_config(self) -> Dict[str, Any]:
        if self._latest:
            return self._latest.contents
        else:
            print(f"No prior configuration found for '{self.app_name}'")

    def _determine_shortform_alias(self, name: str) -> str:
        for char in name:
            if char.isalnum():
                letter = char.lower()
                if letter in self._remaining_letters:
                    self._remaining_letters.remove(letter)
                    return letter

    def _validate_arg_name(self, name: str) -> None:
        if name in self.arguments:
            raise NameError(f"Argument '{name}' already attached to this IOHandler.")


class Argument:
    """Class representing an argument (and its associated metadata) for the IOHandler and ArgsGui to use."""

    def __init__(self, name: str, argtype: Union[type, Callable] = None, default: Any = None, nullable: bool = False, required: bool = None, dependency: Union[Argument, Dependency] = None,
                 choices: Union[Enum, List[Any]] = None, conditions: Union[Callable, List[Callable], Dict[str, Callable]] = None, magnitude: int = None, info: str = None, aliases: List[str] = None) -> None:
        self.name, self.default, self.magnitude, self.info, self._value = name, default, magnitude, info, default

        self.widget: WidgetHandler = None
        self._aliases: List[str] = None

        self.aliases = aliases

        self.dependency = None if dependency is None else (Dependency(dependency, argument=self) if isinstance(dependency, Argument) else dependency.bind(self))
        self.nullable = Nullability(truth=nullable, argument=self)
        self.required = Maybe(required).else_(True if self.default is None and not self.nullable else False)

        self.choices = [member.value for member in choices] if Enum.is_enum(choices) else choices
        self.conditions = [Condition(condition, name=name) for name, condition in conditions.items()] if isinstance(conditions, dict) else (
            [Condition(condition) for condition in conditions] if isinstance(conditions, list) else (
                [Condition(conditions)] if conditions is not None else None
            )
        )

        self.argtype = Validate.Type(argtype, nullable=self.nullable, choices=self.choices)
        if self.conditions:
            self.argtype.conditions = Maybe(self.conditions).else_([])

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __str__(self) -> str:
        return self.name

    @property
    def value(self) -> Any:
        """Property controlling access to the value held by this argument. Setting it will cause validation and coercion to the type of this argument."""
        return self._value

    @value.setter
    def value(self, val: Any) -> None:
        self._value = self.argtype.convert(val)

    @property
    def aliases(self) -> List[str]:
        return self._aliases

    @aliases.setter
    def aliases(self, val: List[str]) -> None:
        self._aliases = [self.name] if val is None else sorted({self.name, *val}, key=len)

    @lazy_property
    def commandline_aliases(self) -> List[str]:
        return [f"--{name}" if len(name) > 1 else f"-{name}" for name in self.aliases]

    def add(self) -> Argument:
        IOHandler.stack[-1].add_argument(argument=self)
        return self


class DependencyMode(AutoEnum):
    ALL, ANY  # noqa


class Dependency:
    def __init__(self, *args: Argument, argument: Argument = None, mode: str = DependencyMode.ANY) -> None:
        self.argument = argument
        self.arguments = list(args)

        if mode == DependencyMode.ANY:
            self.mode = any
        elif mode == DependencyMode.ALL:
            self.mode = all
        else:
            DependencyMode.raise_if_not_a_member(mode)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(argument={self.argument}, arguments=[{', '.join(arg.name for arg in self.arguments)}], mode={self.mode.__name__})"

    def __str__(self) -> str:
        return f"{', '.join(arg.name for arg in self.arguments)} [{self.mode.__name__}]"

    def __bool__(self) -> bool:
        return self.mode([bool(argument.value) for argument in self.arguments])

    def bind(self, argument: Argument) -> Dependency:
        self.argument = argument
        return self

    def validate(self) -> bool:
        if self:
            if self.argument.value is None:
                raise ValueError(f"""Must provide a value for argument '{self.argument}' if {self.mode.__name__} of: {", ".join(f"'{arg}'" for arg in self.arguments)} are truthy.""")
        else:
            if self.argument.value is not None:
                raise ValueError(f"""May not provide a value for argument '{self.argument}' unless {self.mode.__name__} of: {", ".join(f"'{arg}'" for arg in self.arguments)} are truthy.""")

        return True


class Nullability:
    def __init__(self, truth: bool, argument: Argument) -> None:
        self.truth, self.argument = truth, argument

    def __repr__(self) -> str:
        return f"{type(self).__name__}(truth={self.bool}, bool={bool(self)})"

    def __str__(self) -> str:
        return str(self.truth)

    def __bool__(self) -> bool:
        return self.truth if self.argument.dependency is None else True
