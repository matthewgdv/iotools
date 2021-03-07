from __future__ import annotations

from PySide6 import QtWidgets

from .base import WidgetHandler


class Label(WidgetHandler):
    """A manager class for a simple Label widget which can display text."""

    def __init__(self, text: str = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QLabel(text or "")

    def _configure(self) -> None:
        self.widget.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)

    def _get_state(self) -> str:
        return self.widget.text()

    def _set_state(self, val: str) -> None:
        self.widget.setText(val)

    def _get_text(self) -> str:
        return self.widget.text()

    def _set_text(self, val: str) -> None:
        self.widget.setText(val)
