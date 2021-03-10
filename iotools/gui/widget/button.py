from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtWidgets

from iotools.command.argument import BooleanArgument
from .base import WidgetHandler


class Button(WidgetHandler):
    """A manager class for a simple Button widget which can trigger a callback when pushed."""
    _argument_class = BooleanArgument

    def __init__(self, text: str = None, command: Callable = None, state: bool = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QPushButton(text or "")
        self.state = state

        if command is not None:
            self.widget.clicked.connect(command)

    def _get_state(self) -> Optional[bool]:
        return None if not self.widget.isCheckable() else self.widget.isChecked()

    def _set_state(self, val: Optional[bool]) -> None:
        if val is None:
            self.widget.setCheckable(False)
        else:
            if self.state is None:
                self.widget.setCheckable(True)

            self.widget.setChecked(val)

    def _get_text(self) -> str:
        return self.widget.text()

    def _set_text(self, val: str) -> None:
        self.widget.setText(val)
