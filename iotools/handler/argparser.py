from __future__ import annotations

import argparse
from typing import Any, Callable, TYPE_CHECKING


from subtypes import Frame

if TYPE_CHECKING:
    from .iohandler import IOHandler, Argument


class ArgParser(argparse.ArgumentParser):
    """Subclass of argparse.ArgumentParser with its own helptext formatting."""

    def __init__(self, *args: Any, handler: IOHandler = None, **kwargs: Any) -> None:
        self.handler = handler
        super().__init__(*args, **kwargs)

    def add_arguments_from_handler(self) -> None:
        self.add_argument("_", nargs="?")
        for arg in self.handler.arguments.values():
            self.add_argument(*arg.commandline_aliases, default=arg.default, type=self.validate_and_set(arg), choices=arg.choices, required=arg.required, nargs="?" if arg.nullable else None, help=arg.info, dest=arg.name)

    def format_usage(self) -> str:
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, [action for action in self._actions if action.dest != "_"], self._mutually_exclusive_groups)
        return str(formatter.format_help())

    def format_help(self) -> str:
        target_cols = ["name", "commandline_aliases", "argtype", "default", "nullable", "info", "choices", "conditions", "dependency"]
        frame = Frame([arg.__dict__ for arg in self.handler.arguments.values()]).fillna_as_none()

        frame.argtype = frame.argtype.apply(lambda val: str(val))
        frame.commandline_aliases = frame.commandline_aliases.apply(lambda val: ", ".join([str(alias) for alias in val]))
        frame.conditions = frame.conditions.apply(lambda val: val if val is None else ", ".join([cond.name for cond in val]))
        frame.dependency = frame.dependency.apply(lambda val: val if val is None else str(val))

        grouped_frames = dict(tuple(frame.groupby(frame.required.name)))

        detail = ""
        for header, condition in [("Required Arguments:", True), ("Optional Arguments:", False)]:
            if condition in grouped_frames:
                detail += f"{header}\n{Frame(grouped_frames[condition][target_cols]).to_ascii()}\n\n"

        help_text = f"\n{self.format_usage()}"
        help_text += f"\n{self.description or ''}\n\n{detail}{self.epilog or ''}"
        return help_text

    def _get_formatter(self) -> Any:
        return self.formatter_class(prog=self.prog, max_help_position=2000, width=2000)

    @staticmethod
    def validate_and_set(argument: Argument) -> Callable[[Any], bool]:
        def wrapper(candidate: Any) -> bool:
            argument.value = candidate
            return argument.value

        wrapper.__name__ = argument.argtype.converter.__name__
        return wrapper
