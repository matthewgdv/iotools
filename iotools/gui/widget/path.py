from __future__ import annotations

import os
from typing import Any, Tuple

from PySide6 import QtWidgets

from pathmagic import PathLike, Dir

from iotools.command.argument import FileArgument, DirArgument

from .frame import HorizontalFrame
from .label import Label
from .button import Button


class PathSelect(HorizontalFrame):
    """An abstract manager class for a simple PathSelect widget which directs the user to browse for a path."""
    path_method: Any = None
    prompt: str = None

    def __init__(self, state: PathLike = None, padding: Tuple[int, int] = (10, 5), button_on_left: bool = True) -> None:
        super().__init__(margins=0)

        with self:
            self.button, self.label = Button(text='Browse...', command=self.browse).stack(), Label().stack()

        self.button.widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)

        self.set_path(state)

    def set_path(self, path: PathLike) -> None:
        """Set the widget's state to the given path."""
        self.label.state = os.fspath(path if path is not None else Dir.from_desktop())

    def browse(self) -> None:
        """Open an operating-system specific path entry dialog."""
        path_string = self.text
        starting_dir = Dir.from_desktop() if not path_string else (os.path.dirname(path_string) if os.path.isfile(path_string) else path_string)

        selection = self.path_method(caption=self.prompt, dir=str(starting_dir))

        new_path = selection[0] if isinstance(selection, tuple) else selection
        if new_path:
            self.state = os.path.abspath(new_path)

    def _get_state(self) -> Any:
        return self.label.state

    def _set_state(self, val: PathLike) -> Any:
        self.set_path(val)

    def _get_text(self) -> str:
        return self.button.text

    def _set_text(self, val: str) -> None:
        self.button.text = val


class FileSelect(PathSelect):
    """A manager class for a simple FileSelect widget which directs the user to browse for a file."""
    _argument_class = FileArgument
    path_method, prompt = staticmethod(QtWidgets.QFileDialog.getOpenFileName), "Select File"


class DirSelect(PathSelect):
    """A manager class for a simple DirSelect widget which directs the user to browse for a dir."""
    _argument_class = DirArgument
    path_method, prompt = staticmethod(QtWidgets.QFileDialog.getExistingDirectory), "Select Dir"
