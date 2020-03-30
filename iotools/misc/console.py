from __future__ import annotations

import os
import sys
import contextlib
import functools
import types
from typing import Any, Collection, Set, Callable, cast, TypeVar
import ctypes

import colorama
import readchar
import cursor

from maybe import Maybe
from subtypes import Frame
from pathmagic import File, PathLike
from miscutils import is_running_in_ipython

from iotools import res

res = cast(types.ModuleType, res)
FuncSig = TypeVar("FuncSig", bound=Callable)


class Console:
    """Provides console utilities such as the ability to show/hide the console, clearing lines, printing statements with hyphen separators, and offering choices with an interactive interface."""
    SEP = "-"*150
    SEP2 = f"{'-'*150}\n{'-'*150}"

    UP_ONE_LINE = "\033[A"
    CLEAR_CURRENT_LINE = "\033[2K"

    colorama.init()

    class NoOutput:
        pass

    @staticmethod
    def hide_console() -> None:
        """Hide the current application console. Only works on Windows systems."""
        ctypes.WinDLL("user32").ShowWindow(ctypes.WinDLL("kernel32").GetConsoleWindow(), 0)

    @staticmethod
    def show_console() -> None:
        """Show the current application console if it is hidden. Only works on Windows systems."""
        ctypes.WinDLL("user32").ShowWindow(ctypes.WinDLL("kernel32").GetConsoleWindow(), 1)

    @classmethod
    def clear_lines(cls, num: int = 1) -> None:
        """Clear the given number of lines previously displayed on the console."""
        print(f"{cls.UP_ONE_LINE}{cls.CLEAR_CURRENT_LINE}"*num, end="")

    @staticmethod
    def offer_choices(choices: Collection, starting_choice: Any = None, multi_select: bool = False, desc: str = None, helptext: bool = True, display_repr: bool = True) -> Any:
        """
        Interactively offer choices from a collection to the user. The chosen object will be returned.
        A description of the choice can be optionally provided. If multi_select is True, the user may choose multiple items and a list of them will be returned.
        """
        try:
            if is_running_in_ipython():
                return Console.prompt_choices(choices, desc=desc)

            choices = list(choices)
            selected_index = 0 if starting_choice is None else choices.index(starting_choice)

            func = Console._collect_choices if multi_select else Console._collect_choice

            with cursor.HiddenCursor():
                result = func(choices=choices, starting_index=selected_index, desc=desc, helptext=helptext, display_repr=display_repr)

            print("")
            return result
        except KeyboardInterrupt:
            print("\n\nExiting...")
            sys.exit()

    @staticmethod
    def offer_yes_or_no(default: bool, yes_text: str = 'YES', no_text: str = 'NO', desc: str = None) -> bool:
        """Interactively offer the user a binary choice. The choices can be customized and a description of the choice can be optionally provided."""
        mappings = {yes_text: True, no_text: False}
        question = Maybe(desc).else_(f"[{yes_text}/{no_text}]")
        return mappings[Console.offer_choices(mappings, starting_choice=yes_text if default else no_text, desc=question, display_repr=False, helptext=False)]

    @staticmethod
    def prompt_choices(choices: Collection, desc: str = None, fancy: bool = True) -> Any:
        """Prompt the user to type in a choice. A description of the choice can be optionally provided."""
        if desc is not None:
            print(f"\n{desc}\n\n")

        df = Frame([(index + 1, key) for index, key in enumerate(choices)], columns=("number", "option"))
        print(df.to_ascii(fancy=fancy), end="\n\n")

        output, prompt = 0, f"Choose an option: 1-{len(choices)}. 'esc' to exit.\n"
        while output not in list(df.number):
            output = input(prompt).strip()
            if output in ["esc", "quit", "bye", "stop", "help"]:
                raise KeyboardInterrupt()
            else:
                output = int(output)

        choice, = df[df.number == output].option
        return choice

    @staticmethod
    @contextlib.contextmanager
    def surround_sep(character: str = "-", start_sep: bool = True, stop_sep: bool = False, start_lines: int = 1, stop_lines: int = 1, start_length: int = 150, stop_length: int = 150,
                     prefix: str = "\n", suffix: str = "\n", start_padding: str = "\n\n", stop_padding: str = "\n") -> None:
        """Context manager that will print separators of the given lines and length on enter and/or exit (based on provided arguments)."""
        br = "\n"

        print(prefix, end="")
        if start_sep:
            print(f"{((character*start_length + br)*start_lines).strip()}{start_padding}", end="")

        yield

        if stop_sep:
            print(f"{stop_padding}{((character*stop_length + br)*stop_lines).strip()}", end="")
        print(suffix, end="")

    @staticmethod
    def print_sep(text: str = None, character: str = "-", start_sep: bool = True, stop_sep: bool = True, start_lines: int = 1, stop_lines: int = 1,
                  start_length: int = 150, stop_length: int = 150, prefix: str = "\n", suffix: str = "\n", start_padding: str = "\n\n", stop_padding: str = "\n", **kwargs: Any) -> None:
        """Print the given string with separators of the given lines and length before and/or after (based on provided arguments)."""
        with Console.surround_sep(character=character, start_sep=start_sep, stop_sep=stop_sep, start_lines=start_lines, stop_lines=stop_lines, start_length=start_length, stop_length=stop_length, prefix=prefix, suffix=suffix, start_padding=start_padding, stop_padding=stop_padding):
            if text is not None:
                print(text, **kwargs)

    @staticmethod
    def _collect_choice(choices: list, starting_index: int, desc: str, helptext: bool, display_repr: bool) -> Any:
        if helptext:
            print("Up/Down to navigate. Enter to choose and continue. Esc to exit.", end="\n\n")

        if desc is not None:
            print(desc, end="\n\n")

        output, current_index = Console.NoOutput, starting_index
        while output is Console.NoOutput:
            print("\n".join([f"{'[x]' if index == current_index else '[ ]'} {repr(choice) if display_repr else choice}" for index, choice in enumerate(choices)]))

            while True:
                keypress = readchar.readkey()
                if keypress == readchar.key.UP:
                    current_index = max(current_index - 1, 0)
                    break
                elif keypress == readchar.key.DOWN:
                    current_index = min(current_index + 1, len(choices) - 1)
                    break
                elif keypress == readchar.key.ENTER:
                    output = choices[current_index]
                    break
                elif keypress == readchar.key.ESC:
                    raise KeyboardInterrupt()

            if output is Console.NoOutput:
                Console.clear_lines(len(choices))

        return output

    @staticmethod
    def _collect_choices(choices: list, starting_index: int, desc: str, helptext: bool, display_repr: bool) -> Any:
        if helptext:
            print("Up/Down to navigate. Right to add a choice. Left to remove a choice. Enter to continue. Esc to exit.", end="\n\n")

        if desc is not None:
            print(desc, end="\n\n")

        current_index, finished = starting_index, False
        selected_indices: Set[int] = set()
        while not finished:
            print("\n".join([f"{'>' if index == current_index else ' '} {'[x]' if index in selected_indices else '[ ]'} {repr(choice) if display_repr else choice}" for index, choice in enumerate(choices)]))

            while True:
                keypress = readchar.readkey()
                if keypress == readchar.key.UP:
                    current_index = max(current_index - 1, 0)
                    break
                elif keypress == readchar.key.DOWN:
                    current_index = min(current_index + 1, len(choices) - 1)
                    break
                if keypress == readchar.key.RIGHT:
                    selected_indices.add(current_index)
                    break
                elif keypress == readchar.key.LEFT:
                    selected_indices.discard(current_index)
                    break
                elif keypress == readchar.key.ENTER:
                    finished = True
                    break
                elif keypress == readchar.key.ESC:
                    raise KeyboardInterrupt()

            if not finished:
                Console.clear_lines(len(choices))

        return [choices[index] for index in selected_indices]


class SysTrayApp:
    """Context manager for systemtray-based applications. The console is hidden on entering and shown again on exiting."""

    def __init__(self, hover_text: str = "Placeholder program description.", icon: PathLike = None, default_menu_index: int = 0, on_quit: Callable = None) -> None:
        from infi.systray import SysTrayIcon

        icon = Maybe(icon).else_(File.from_resource(package=res, name="python_icon", extension="ico"))
        on_quit = Maybe(on_quit).else_(SysTrayApp._kill)

        self.tray = SysTrayIcon(icon=os.fspath(icon), hover_text=hover_text, on_quit=on_quit, default_menu_index=default_menu_index)

    def __enter__(self) -> SysTrayApp:
        Console.hide_console()
        return self.tray.__enter__()

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        Console.show_console()
        if ex_type is None:
            self.tray.__exit__(ex_type, ex_value, ex_traceback)

    @staticmethod
    def _kill(systray: Any) -> None:
        Console.show_console()
        raise KeyboardInterrupt("The app was closed using the system tray's 'quit' option.")


class Colorama:
    """Context manager/decorator class used to initialize and deinitialize colorama."""

    def __init__(self) -> None:
        self.colorama = colorama

    def __call__(self, func: FuncSig = None) -> FuncSig:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with type(self)():
                ret = func(*args, **kwargs)
            return ret

        return cast(FuncSig, wrapper)

    def __enter__(self) -> Colorama:
        self.previous = sys.stdout
        sys.stdout = Console.DEFAULT_STDOUT
        colorama.init()
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        colorama.deinit()
        sys.stdout = self.previous
