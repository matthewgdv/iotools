from __future__ import annotations

from typing import Any

from PySide6 import QtWidgets

from iotools.command.argument import StringArgument

from .base import WidgetHandler


class Text(WidgetHandler):
    """A manager class for a simple text Text widget which can capture text and has editor-like features."""
    _argument_class = StringArgument

    def __init__(self, state: str = None, magnitude: int = 1, **kwargs: Any) -> None:
        super().__init__()

        self.widget = QtWidgets.QTextEdit()
        self.magnitude = magnitude or 1
        self.state = state

    def _configure(self) -> None:
        self.widget.setMaximumHeight(24*self.magnitude)

    def _get_state(self) -> Any:
        return self.widget.toPlainText()

    def _set_state(self, val: Any) -> Any:
        self.widget.setText(str(val or ""))


class Entry(WidgetHandler):
    """A manager class for a simple text Entry widget which can capture text."""
    _argument_class = StringArgument

    def __init__(self, state: str = None) -> None:
        super().__init__()
        self.widget = QtWidgets.QLineEdit()
        self.state = state

    def _get_state(self) -> str:
        return self.widget.text()

    def _set_state(self, val: str) -> None:
        self.widget.setText(str(val or ""))
