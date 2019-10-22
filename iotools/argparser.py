from __future__ import annotations

import argparse
from typing import Any, TYPE_CHECKING


from subtypes import Frame

if TYPE_CHECKING:
    from .synchronizer import Synchronizer


class ArgParser(argparse.ArgumentParser):
    """Subclass of argparse.ArgumentParser with its own helptext formatting."""

    def __init__(self, *args: Any, sync: Synchronizer = None, **kwargs: Any) -> None:
        self.sync = sync
        super().__init__(*args, **kwargs)

    def add_arguments_from_handler(self) -> None:
        self.add_argument("_", nargs="?")
        for arg in self.sync.root.handler.arguments.values():
            self.add_argument(*arg.commandline_aliases, default=arg.default, type=arg.argtype, choices=arg.choices, required=not arg.optional, nargs="?" if arg.nullable else None, help=arg.info, dest=arg.name)

    def format_usage(self) -> str:
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, [action for action in self._actions if action.dest != "_"], self._mutually_exclusive_groups)
        return str(formatter.format_help())

    def format_help(self) -> str:
        target_cols = ["name", "commandline_aliases", "argtype", "default", "nullable", "info", "choices", "condition"]
        frame = Frame([arg.__dict__ for arg in self.sync.root.handler.arguments.values()])
        frame = frame.fillna_as_none()
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