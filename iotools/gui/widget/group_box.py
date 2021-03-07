from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

from .base import WidgetHandler


class GroupBox(WidgetHandler):
    layout_constructor = QtWidgets.QGridLayout

    def __init__(self, text: str, state: bool = None) -> None:
        super().__init__()

        self.widget, self.layout = QtWidgets.QGroupBox(), self.layout_constructor()
        self.widget.setLayout(self.layout)

        self.text, self.state = text, state

    def _get_state(self) -> Optional[bool]:
        return None if not self.widget.isCheckable() else self.widget.isChecked()

    def _set_state(self, val: Optional[bool]) -> None:
        self.widget.setCheckable(val is not None)
        if val is not None:
            self.widget.setChecked(val)

    def _get_text(self) -> str:
        return self.widget.title()

    def _set_text(self, val: str) -> None:
        self.widget.setTitle(val)


class HorizontalGroupBox(GroupBox):
    layout_constructor = QtWidgets.QHBoxLayout


class VerticalGroupBox(GroupBox):
    layout_constructor = QtWidgets.QVBoxLayout

