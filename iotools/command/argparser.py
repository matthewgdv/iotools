from __future__ import annotations

import argparse
from typing import Any, Callable, TYPE_CHECKING

import tabulate

if TYPE_CHECKING:
    from .declarative import CommandHandler
    from .argument import Argument


class ArgParser(argparse.ArgumentParser):
    """Subclass of argparse.ArgumentParser with its own helptext formatting."""

    def __init__(self, *args: Any, handler: CommandHandler = None, **kwargs: Any) -> None:
        self.handler = handler
        super().__init__(*args, **kwargs)

    def add_arguments_from_handler(self) -> None:
        self.add_argument("_", nargs="?")
        for arg in self.handler.arguments:
            self.add_argument(*arg.aliases, default=arg.default, type=self.validate_and_set(arg), choices=arg.choices, required=arg.required, nargs="?" if arg.nullable else None, help=arg.info, dest=arg.name)

    def format_usage(self) -> str:
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, [action for action in self._actions if action.dest != "_"], self._mutually_exclusive_groups)
        return str(formatter.format_help())

    def format_help(self) -> str:
        target_cols = ["name", "commandline_aliases", "type", "default", "nullable", "info", "choices", "conditions"]

        required_args, optional_args = [], []

        for arg in self.handler.arguments:
            record = (
                arg.name,
                ", ".join(arg.aliases),
                arg.validator.type_affinity.__name__,
                arg.default,
                arg.nullable,
                arg.info,
                arg.choices,
                ", ".join(str(cond) for cond in arg.validator.conditions)
            )

            (required_args if arg.required else optional_args).append(record)

        required = f"Required Arguments\n{tabulate.tabulate(required_args, headers=target_cols, tablefmt='fancy_grid')}"
        optional = f"Optional Arguments\n{tabulate.tabulate(optional_args, headers=target_cols, tablefmt='fancy_grid')}"

        return f"\n{self.format_usage()}\n{self.description or ''}\n\n{required}\n\n{optional}\n\n{self.epilog or ''}"

    def _get_formatter(self) -> Any:
        return self.formatter_class(prog=self.prog, max_help_position=2000, width=2000)

    @staticmethod
    def validate_and_set(argument: Argument) -> Callable[[Any], bool]:
        def wrapper(candidate: Any) -> bool:
            argument.value = candidate
            return argument.value

        wrapper.__name__ = argument.validator.type_affinity.__name__
        return wrapper
