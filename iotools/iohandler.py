from __future__ import annotations

import argparse
import inspect
import os
import sys
from typing import Any, Callable, Dict, List, Union

from maybe import Maybe
from subtypes import Enum, Frame, Str
from pathmagic import File, Dir
from miscutils import is_running_in_ipython, NameSpace

from .widget.widget import WidgetManager
from .gui.argsgui import ArgsGui
from .validator.validator import Validate
from .validator import StringValidator, IntegerValidator, FloatValidator, BoolValidator, ListValidator, DictionaryValidator, PathValidator, FileValidator, DirValidator, DateTimeValidator

# TODO: implement argument profiles


class RunMode(Enum):
    SMART, COMMANDLINE, GUI, PROGRAMMATIC = "smart", "commandline", "gui", "programmatic"


class ArgType(Enum):
    String, Integer, Float, Boolean, List, Dict = StringValidator, IntegerValidator, FloatValidator, BoolValidator, ListValidator, DictionaryValidator
    Path, File, Dir = PathValidator, FileValidator, DirValidator
    DateTime, Frame = DateTimeValidator, Frame


class IOHandler:
    """
    A class that handles I/O by collecting arguments through the commandline, or generates a GUI to collect arguments if no commandline arguments are provided.
    Once instantiated, the collected arguments can be accessed by item access on the object (similar to a dict).
    The IOHandler implicitly creates a folder structure in the directory of its script for storing the configuration of the previous run, and for providing output.
    """

    def __init__(self, app_name: str = None, app_desc: str = "", run_mode: str = RunMode.SMART) -> None:
        self.app_name, self.app_desc, self.run_mode = app_name, app_desc, run_mode
        self.args = NameSpace()
        self.outfile = self._latest = None  # type: File
        self.outdir: Dir = None
        self._arguments: List[Argument] = []

        self._workfolder_setup()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    @property
    def arguments(self) -> List[Argument]:
        return self._arguments

    def add_arg(self, name: str, aliases: List[str] = None, argtype: Union[type, Callable] = None, default: Any = None, nullable: bool = False, optional: bool = None,
                choices: List[Any] = None, condition: Callable = None, magnitude: int = None, info: str = None) -> None:

        self._validate_arg_name(name)

        if aliases is None:
            aliases = []

        shortform = self._determine_shortform_alias(name)
        aliases = [shortform, *aliases] if shortform is not None else aliases

        arg = Argument(name=name, aliases=aliases, argtype=argtype, default=default, optional=optional, nullable=nullable, choices=choices, condition=condition, magnitude=magnitude, info=info)
        self._arguments.append(arg)

    def collect_input(self, arguments: Dict[str, Any] = None) -> NameSpace:
        if self.run_mode == RunMode.COMMANDLINE:
            self._run_from_commandline()
        elif self.run_mode == RunMode.GUI:
            self._run_as_gui(arguments=arguments)
        elif self.run_mode == RunMode.PROGRAMMATIC:
            self._run_programatically(arguments=arguments)
        elif self.run_mode == RunMode.SMART:
            if is_running_in_ipython() or inspect.getmodule(inspect.stack()[1][0]).__name__ != "__main__":
                self._run_programatically(arguments=arguments)
            else:
                if not sys.argv[1:]:
                    self._run_as_gui(arguments=arguments)
                else:
                    self._run_from_commandline()
        else:
            RunMode.raise_if_not_a_member(self.run_mode)

        self._generate_attributes_from_args()
        self._save_latest_input_config()

        return self.args

    def show_output(self, outfile: bool = True, outdir: bool = True) -> None:
        if outfile:
            self.outfile.open()
        if outdir:
            self.outdir.open()

    def clear_output(self, outfile: bool = True, outdir: bool = True) -> None:
        if outfile:
            self.outfile.contents = ""

        if outdir:
            self.outdir.clear()

    def _run_as_gui(self, arguments: Dict[str, Any]) -> None:
        if arguments:
            self._set_new_argument_defaults(arguments)

        ArgsGui(handler=self)

    def _run_from_commandline(self) -> None:
        ArgsCommandLineParser(handler=self)

    def _run_programatically(self, arguments: Dict[str, Any]) -> None:
        if arguments:
            self._set_arguments_directly(arguments)

    def _save_latest_input_config(self) -> None:
        self._latest.contents = {arg.name: arg.value for arg in self.arguments}

    def _load_latest_input_config(self) -> Dict[str, Any]:
        if self._latest:
            return self._latest.contents
        else:
            print(f"No prior configuration found for '{self.app_name}'")
            raise FileNotFoundError()

    def _determine_shortform_alias(self, name: str) -> str:
        for letter in name:
            if letter.isalnum():
                failed = False
                for arg in self.arguments:
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
        if name in [argument.name for argument in self._arguments]:
            raise NameError(f"Argument '{name}' already attached to this IOHandler.")
        if not name.isidentifier():
            raise NameError(f"Argument name '{name}' is not a valid Python identifier.")

    def _set_arguments_directly(self, arguments: Dict[str, Any]) -> None:
        for argument in self.arguments:
            for name, val in arguments.items():
                if argument.name == name:
                    argument.value = val
                    break

    def _set_new_argument_defaults(self, arguments: Dict[str, Any]) -> None:
        for argument in self.arguments:
            for name, val in arguments.items():
                if argument.name == name:
                    argument.default = val
                    break

    def _generate_attributes_from_args(self) -> None:
        for arg in self.arguments:
            self.args[arg.name] = arg.value

    def _workfolder_setup(self) -> None:
        if is_running_in_ipython():
            current_dir = os.getcwd()
            self.app_name = Maybe(self.app_name).else_("unknown")
        else:
            main = File.from_main()
            current_dir = main.dir.path
            self.app_name = Maybe(self.app_name).else_(main.prename)

        workfolder = Dir(current_dir).newdir("__workfolders__").newdir(self.app_name)
        self.outfile, self.outdir, self._latest = workfolder.newfile("output", "txt"), workfolder.newdir("output"), workfolder.newfile("latest", "pkl")


class Argument:
    def __init__(self, name: str, aliases: List[str] = None, argtype: Union[type, Callable] = None, default: Any = None, nullable: bool = False, optional: bool = None,
                 choices: List[Any] = None, condition: Callable = None, magnitude: int = None, info: str = None) -> None:
        self.name, self.aliases, self.default, self.nullable, self.magnitude, self.info, self._value = name, aliases, default, nullable, magnitude, info, default

        self.choices = [member.value for member in choices] if Enum.is_enum(choices) else (choices if choices is None else list(choices))
        self.optional = Maybe(optional).else_(True if self.default is not None or self.nullable else False)
        self.condition = Condition(condition) if condition is not None else None

        self.argtype = Validate.Type(argtype, nullable=self.nullable, choices=self.choices)
        if self.condition:
            self.argtype.conditions = [self.condition]

        self.aliases = [self.name, *self.aliases] if self.aliases is not None else [self.name]
        self._argparse_aliases: List[str] = [f"--{name}" if len(name) > 1 else f"-{name}" for name in self.aliases]
        self._widget: WidgetManager = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __str__(self) -> str:
        return self.name

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, val: Any) -> None:
        self._value = self.argtype.convert(val)


class Condition:
    def __init__(self, condition: Callable[..., bool]) -> None:
        self.condition = condition

    def __call__(self, input_val: Any) -> bool:
        return self.condition(input_val)

    def __repr__(self) -> str:
        if self.condition is None:
            return ""
        elif "<lambda>" in repr(self.condition):
            return str(Str(inspect.getsource(self.condition)).search(r"condition\s*=\s*lambda.*:\s*(([^([,]*(\(.*?\)|\[.*?\])+)*[^([,]*?)[,)]").group(1))
        else:
            return self.condition.__name__


class ArgsCommandLineParser:
    def __init__(self, handler: IOHandler, args: List[str] = None) -> None:
        self.handler = handler

        parser = ArgParser(prog=self.handler.app_name, description=self.handler.app_desc, handler=self.handler)
        parser.add_argument("_", nargs="?")
        for arg in self.handler.arguments:
            parser.add_argument(*arg._argparse_aliases, default=arg.default, choices=arg.choices, required=not arg.optional, nargs="?" if arg.nullable else None, help=arg.info, dest=arg.name)

        namespace = parser.parse_args() if args is None else parser.parse_args(args)
        for arg in self.handler.arguments:
            arg.value = getattr(namespace, arg.name)


class ArgParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, handler: IOHandler = None, **kwargs: Any) -> None:
        self.handler = handler
        super().__init__(*args, **kwargs)

    def format_usage(self) -> str:
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, [action for action in self._actions if action.dest != "_"], self._mutually_exclusive_groups)
        return str(formatter.format_help())

    def format_help(self) -> str:
        target_cols = ["name", "aliases", "argtype", "default", "nullable", "info", "choices", "condition"]
        frame = Frame([arg.__dict__ for arg in self.handler.arguments])
        frame = frame.fillna_as_none()
        frame.aliases = frame._argparse_aliases
        frame.argtype = frame.argtype.apply(lambda val: val.converter.__name__)
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
