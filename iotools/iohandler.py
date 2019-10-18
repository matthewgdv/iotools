from __future__ import annotations

import argparse
import inspect
import sys
from typing import Any, Callable, Dict, List, Union

from maybe import Maybe
from subtypes import Enum, Frame, Str
from miscutils import NameSpaceDict
import miscutils

from .widget import WidgetHandler
from .argsgui import ArgsGui
from .validator import Validate, StringValidator, IntegerValidator, FloatValidator, BoolValidator, ListValidator, DictionaryValidator, PathValidator, FileValidator, DirValidator, DateTimeValidator
import iotools

# TODO: implement argument profiles
# TODO: implement mutually exclusive argument gruops
# TODO: implement dependent arguments


class RunMode(Enum):
    """An Enum of the various run modes an IOHandler accepts."""
    SMART, COMMANDLINE, GUI, PROGRAMMATIC = "smart", "commandline", "gui", "programmatic"


class ArgType(Enum):
    """An Enum of the various argument types an IOHandler understands."""
    String, Integer, Float, Boolean, List, Dict = StringValidator, IntegerValidator, FloatValidator, BoolValidator, ListValidator, DictionaryValidator
    Path, File, Dir = PathValidator, FileValidator, DirValidator
    DateTime, Frame = DateTimeValidator, Frame


class Config(miscutils.Config):
    """A config class granting access to an os-specific appdata directory for use by this application."""
    app_name = iotools.__name__


class IOHandler:
    """
    A class that handles I/O by collecting arguments through the commandline, or generates a GUI to collect arguments if no commandline arguments are provided.
    Once instantiated, the collected arguments can be accessed through its 'args' namespace attribute.
    The IOHandler implicitly creates a folder structure in the directory of its script for storing the configuration of the previous run, and for providing output.
    """

    def __init__(self, app_name: str, app_desc: str = "", name: str = None, run_mode: str = RunMode.SMART, config: Config = None) -> None:
        self.app_name, self.app_desc, self.name, self.run_mode, self.config = app_name, app_desc, Maybe(name).else_(app_name), run_mode, Config() if config is None else config
        self.arguments: Dict[str, Argument] = {}
        self.subcommands: Dict[str, IOHandler] = {}
        self.args: NameSpaceDict = None
        self._parser: ArgParser = None

        workfolder = self.config.appdata.new_dir(self.app_name).new_dir(self.name)
        self.outfile, self.outdir, self._latest = workfolder.new_file("output", "txt"), workfolder.new_dir("output"), workfolder.new_file("latest", "pkl")

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __getitem__(self, key: str) -> Any:
        return self.subcommands[key]

    def add_arg(self, name: str, aliases: List[str] = None, argtype: Union[type, Callable] = None, default: Any = None, nullable: bool = False, optional: bool = None,
                choices: List[Any] = None, condition: Callable = None, magnitude: int = None, info: str = None) -> Argument:
        """Add a new Argument object to this IOHandler. Passes on its arguments to the Argument constructor."""

        self._validate_arg_name(name)
        shortform = self._determine_shortform_alias(name)

        aliases = [] if aliases is None else aliases
        aliases = [shortform, *aliases] if shortform is not None else aliases

        arg = Argument(name=name, aliases=aliases, argtype=argtype, default=default, optional=optional, nullable=nullable, choices=choices, condition=condition, magnitude=magnitude, info=info)
        self.arguments[name] = arg

        return arg

    def add_subcommand(self, name: str) -> IOHandler:
        """Add a new subcommand to this IOHandler, which is itself an IOHandler. The subcommand will process its own set of arguments when the given verb is used."""
        subcommand = IOHandler(app_name=self.app_name, app_desc=self.app_desc, name=name, run_mode=self.run_mode, config=self.config)
        self.subcommands[name] = subcommand
        return subcommand

    def collect_input(self, arguments: Dict[str, Any] = None, subcommand: str = None) -> NameSpaceDict:
        """Collect input using this IOHandler's 'run_mode' and return a NameSpaceDict holding the parsed arguments, coerced to appropriate python types."""
        if self.run_mode == RunMode.COMMANDLINE:
            self._run_from_commandline()
        elif self.run_mode == RunMode.GUI:
            self._run_as_gui(arguments=arguments, subcommand=subcommand)
        elif self.run_mode == RunMode.PROGRAMMATIC:
            self._run_programatically(arguments=arguments, subcommand=subcommand)
        elif self.run_mode == RunMode.SMART:
            if subcommand or arguments:
                self._run_programatically(arguments=arguments, subcommand=subcommand)
            else:
                if not sys.argv[1:]:
                    self._run_as_gui(arguments=arguments, subcommand=subcommand)
                else:
                    self._run_from_commandline()
        else:
            RunMode.raise_if_not_a_member(self.run_mode)

        self._save_latest_input_config()

        return self.args

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

    def _run_programatically(self, arguments: Dict[str, Any], subcommand: str = None) -> None:
        if arguments:
            self._set_arguments_directly(arguments, subcommand=subcommand)

        self.args = NameSpaceDict({name: arg.value for name, arg in self.arguments.items()})

    def _run_as_gui(self, arguments: Dict[str, Any], subcommand: str = None) -> None:
        if arguments:
            self._set_new_argument_defaults(arguments, subcommand=subcommand)

        ArgsGui(handler=self)
        self.args = NameSpaceDict({name: arg.value for name, arg in self.arguments.items()})

    def _run_from_commandline(self, args: List[str] = None) -> None:
        self._parser = ArgParser(prog=self.app_name, description=self.app_desc, handler=self)
        self._parser.add_arguments_from_handler()

        self._recursively_add_subcommands()

        self.args = NameSpaceDict(vars(self._parser.parse_args() if args is None else self._parser.parse_args(args)))

    def _recursively_add_subcommands(self) -> None:
        if self.subcommands:
            subparsers = self._parser.add_subparsers()
            for name, subcommand in self.subcommands.items():
                subcommand._parser = subparsers.add_parser(name, prog=subcommand.app_name, description=subcommand.app_desc, handler=subcommand)
                subcommand._parser.add_arguments_from_handler()
                subcommand._recursively_add_subcommands()

    def _save_latest_input_config(self) -> None:
        self._latest.contents = self.args

    def _load_latest_input_config(self) -> Dict[str, Any]:
        if self._latest:
            return self._latest.contents
        else:
            print(f"No prior configuration found for '{self.app_name}'")
            raise FileNotFoundError()

    def _determine_shortform_alias(self, name: str) -> str:
        for letter in name:
            if letter.isalnum():
                failed = letter == "h"
                for arg in self.arguments.values():
                    for alias in arg.aliases:
                        if letter == alias:
                            failed = True
                        if failed:
                            break
                    if failed:
                        break
                else:
                    return letter

    def _validate_arg_name(self, name: str) -> None:
        if name in self.arguments:
            raise NameError(f"Argument '{name}' already attached to this IOHandler.")

    def _set_arguments_directly(self, arguments: Dict[str, Any], subcommand: str = None) -> None:
        handler = self if subcommand is None else self.subcommands[subcommand]
        for name, val in arguments.items():
            handler.arguments[name].value = val

    def _set_new_argument_defaults(self, arguments: Dict[str, Any], subcommand: str = None) -> None:
        handler = self if subcommand is None else self.subcommands[subcommand]
        for name, val in arguments.items():
            handler.arguments[name].default = val


class Argument:
    """Class representing an argument (and its associated metadata) for the IOHandler and ArgsGui to use."""

    def __init__(self, name: str, aliases: List[str] = None, argtype: Union[type, Callable] = None, default: Any = None, nullable: bool = False, optional: bool = None,
                 choices: List[Any] = None, condition: Callable = None, magnitude: int = None, info: str = None) -> None:
        self.name, self.aliases, self.default, self.nullable, self.magnitude, self.info, self._value = name, aliases, default, nullable, magnitude, info, default

        self.choices = choices.values if Enum.is_enum(choices) else (list(choices) if choices is not None else None)
        self.optional = Maybe(optional).else_(True if self.default is not None or self.nullable else False)
        self.condition = Condition(condition) if condition is not None else None

        self.argtype = Validate.Type(argtype, nullable=self.nullable, choices=self.choices)
        if self.condition:
            self.argtype.conditions = [self.condition]

        self.aliases = [self.name, *self.aliases] if self.aliases is not None else [self.name]
        self._argparse_aliases: List[str] = [f"--{name}" if len(name) > 1 else f"-{name}" for name in self.aliases]
        self._widget: WidgetHandler = None

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


class Condition:
    """Class representing a condition which an argument value must fulfill in order to be valid."""

    def __init__(self, condition: Callable[..., bool]) -> None:
        self.condition = condition

    def __call__(self, input_val: Any) -> bool:
        return self.condition(input_val)

    def __repr__(self) -> str:
        if self.condition is None:
            return ""
        elif "<lambda>" in repr(self.condition):
            return str(Str(inspect.getsource(self.condition)).re.search(r"condition\s*=\s*lambda.*:\s*(([^([,]*(\(.*?\)|\[.*?\])+)*[^([,]*?)[,)]").group(1))
        else:
            return self.condition.__name__


class ArgParser(argparse.ArgumentParser):
    """Subclass of argparse.ArgumentParser with its own helptext formatting."""

    def __init__(self, *args: Any, handler: IOHandler = None, **kwargs: Any) -> None:
        self.handler = handler
        super().__init__(*args, **kwargs)

    def add_arguments_from_handler(self) -> None:
        self.add_argument("_", nargs="?")
        for arg in self.handler.arguments.values():
            self.add_argument(*arg._argparse_aliases, default=arg.default, type=arg.argtype, choices=arg.choices, required=not arg.optional, nargs="?" if arg.nullable else None, help=arg.info, dest=arg.name)

    def format_usage(self) -> str:
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, [action for action in self._actions if action.dest != "_"], self._mutually_exclusive_groups)
        return str(formatter.format_help())

    def format_help(self) -> str:
        target_cols = ["name", "aliases", "argtype", "default", "nullable", "info", "choices", "condition"]
        frame = Frame([arg.__dict__ for arg in self.handler.arguments.values()])
        frame = frame.fillna_as_none()
        frame.aliases = frame._argparse_aliases
        frame.argtype = frame.argtype.apply(lambda val: str(val))
        grouped_frames = dict(tuple(frame.groupby("optional")))

        detail = ""
        for header, condition in [("Mandatory Arguments:", False), ("Optional Arguments:", True)]:
            if condition in grouped_frames:
                detail += f"{header}\n{Frame(grouped_frames[condition][target_cols]).to_ascii()}\n\n"

        help_text = f"\n{self.format_usage()}"
        help_text += f"\n{self.description or ''}\n\n{detail}{self.epilog or ''}"
        return help_text

    def _get_formatter(self) -> Any:
        return self.formatter_class(prog=self.prog, max_help_position=2000, width=2000)
