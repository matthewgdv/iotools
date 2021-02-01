from __future__ import annotations

import string
import sys
from typing import Any, Callable, Union, Optional, Type, Tuple, TYPE_CHECKING

from maybe import Maybe
from subtypes import Enum, ValueEnum, Dict, DoNotTranslateMeta
from miscutils import cached_property, is_running_in_ipython

from .synchronizer import Synchronizer

from iotools.misc import Validate, Condition, Validator, IoToolsConfig as Config

if TYPE_CHECKING:
    from iotools.gui.widget import WidgetHandler


# TODO: implement argument profiles
# TODO: improve dependent arguments


class RunMode(Enum):
    """An Enum of the various run modes an IOHandler accepts."""
    SMART, COMMANDLINE, GUI, PROGRAMMATIC = "smart", "commandline", "gui", "programmatic"


class ArgType(ValueEnum):
    """An Enum of the various argument types an IOHandler understands."""
    STRING, BOOLEAN, INTEGER, FLOAT, DECIMAL = Validate.String, Validate.Boolean, Validate.Integer, Validate.Float, Validate.Decimal
    DATETIME, DATE = Validate.DateTime, Validate.Date
    LIST, DICT, SET = Validate.List, Validate.Dict, Validate.Set
    PATH, FILE, DIR = Validate.Path, Validate.File, Validate.Dir


class ImplicitNone:
    pass


implicit_none = ImplicitNone()


class IOHandler:
    """
    A class that handles I/O by collecting arguments through the commandline, or generates a GUI to collect arguments if no commandline arguments are provided.
    The IOHandler implicitly creates a folder structure in the directory of its script for storing the configuration of the previous run, and for providing output.
    """

    stack: list[IOHandler] = []

    def __init__(self, app_name: str, app_desc: str = "", run_mode: RunMode = None, callback: Callable = None, subtypes: bool = True, _name: str = None, _parent: IOHandler = None) -> None:
        self.app_name, self.app_desc, self.run_mode, self.callback, self.subtypes, self.name, self.parent = app_name, app_desc, run_mode or RunMode.SMART, callback, subtypes, Maybe(_name).else_("main"), _parent
        self.config = Config() if self.parent is None else self.parent.config

        self.arguments: dict[str, Argument] = {}
        self.subcommands: dict[str, IOHandler] = {}
        self.sync: Optional[Synchronizer] = None

        self._remaining_letters = set(string.ascii_lowercase)
        self._remaining_letters.discard("h")

        self._root = (self.config.folder.new_dir(self.app_name) if self.parent is None else self.parent._root).new_dir(self.name)
        self._dir = self._root.new_dir("__io__")
        self.outfile, self.outdir, self._latest = self._dir.new_file("output", "txt"), self._dir.new_dir("output"), self._dir.new_file("latest", "pkl")

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

        if isinstance(argument.argtype, Validator):
            argument.argtype.use_subtypes = self.subtypes

        self.arguments[argument.name] = argument

    def add_subcommand(self, name: str, callback: Callable = None) -> IOHandler:
        """Add a new subcommand to this IOHandler, which is itself an IOHandler. The subcommand will process its own set of arguments when the given verb is used."""
        subcommand = IOHandler(app_name=self.app_name, app_desc=self.app_desc, run_mode=self.run_mode, callback=callback, _name=name, _parent=self)
        self.subcommands[name] = subcommand
        return subcommand

    def process(self, values: Union[dict, ImplicitNone] = implicit_none, handler: IOHandler = None) -> CallableDict:
        """Collect input using this IOHandler's 'run_mode' and return a CallableDict holding the parsed arguments, coerced to appropriate python types."""
        self.sync = Synchronizer(root_handler=self)
        namespace, handler = self._delegate_to_synchronizer(values=values, handler=handler)

        handler._save_latest_input_config(namespace=namespace)
        return CallableDict(dictionary=namespace, callback=handler.callback)

    def show_output(self, outfile: bool = True, outdir: bool = True) -> None:
        """Show the output file and/or folder belonging to this IOHandler."""
        if outfile:
            self.outfile.start()
        if outdir:
            self.outdir.start()

    def clear_output(self, outfile: bool = True, outdir: bool = True) -> None:
        """Clear the output file and/or folder belonging to this IOHandler."""
        if outfile:
            self.outfile.content = None

        if outdir:
            self.outdir.clear()

    def _delegate_to_synchronizer(self, values: Union[dict, ImplicitNone], handler: IOHandler) -> Tuple[Dict, IOHandler]:
        if self.run_mode == RunMode.SMART:
            return self._run_smart(values=values, handler=handler)
        else:
            handler_method = RunMode(self.run_mode).map_to({
                RunMode.COMMANDLINE: self.sync.run_from_commandline,
                RunMode.GUI: self.sync.run_as_gui,
                RunMode.PROGRAMMATIC: self.sync.run_programatically,
            })

            return handler_method(values=None if values is implicit_none else values, handler=handler)

    def _run_smart(self, values: Union[dict, ImplicitNone], handler: IOHandler) -> Tuple[Dict, IOHandler]:
        if values or is_running_in_ipython():
            return self.sync.run_programatically(values=values, handler=handler)
        else:
            if values is implicit_none:
                values = None

            if not sys.argv[1:]:
                return self.sync.run_as_gui(values=values, handler=handler)
            else:
                return self.sync.run_from_commandline(values=values, handler=handler)

    def _save_latest_input_config(self, namespace: Dict) -> None:
        self._latest.content = namespace

    def _load_latest_input_config(self) -> dict[str, Any]:
        if self._latest:
            return self._latest.content
        else:
            print(f"No prior configuration found for '{self.name}'")

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
                 choices: Union[Type[Enum], list[Any]] = None, conditions: Union[Callable, list[Callable], dict[str, Callable]] = None, magnitude: int = None, info: str = None, aliases: list[str] = None, widget_kwargs: dict = None) -> None:
        self.name, self.default, self.magnitude, self.info, self._value, self.widget_kwargs = name, default, magnitude, info, default, widget_kwargs or {}

        self.widget: Optional[WidgetHandler] = None
        self._aliases: Optional[list[str]] = None

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
    def aliases(self) -> list[str]:
        return self._aliases

    @aliases.setter
    def aliases(self, val: list[str]) -> None:
        self._aliases = [self.name] if val is None else sorted({self.name, *val}, key=len)

    @cached_property
    def commandline_aliases(self) -> list[str]:
        return [f"--{name}" if len(name) > 1 else f"-{name}" for name in self.aliases]

    def add(self, handler: IOHandler = None) -> Argument:
        (IOHandler.stack[-1] if handler is None else handler).add_argument(argument=self)
        return self


class Dependency:
    class Mode(Enum):
        ALL, ANY = "all", "any"

    def __init__(self, *args: Argument, argument: Argument = None, mode: Dependency.Mode = Mode.ANY) -> None:
        self.argument, self.arguments, self.mode = argument, list(args), self.Mode(mode).map_to({self.Mode.ALL: all, self.Mode.ANY: any})

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
        return f"{type(self).__name__}(truth={self.truth}, bool={bool(self)})"

    def __str__(self) -> str:
        return str(self.truth)

    def __bool__(self) -> bool:
        return self.truth if self.argument.dependency is None else True


class CallableDict(Dict, metaclass=DoNotTranslateMeta):
    def __init__(self, dictionary: Dict, callback: Callable = None) -> None:
        super().__init__(dictionary)
        self._callback_ = callback

    def __call__(self) -> Any:
        return self if self._callback_ is None else self._callback_(self)
