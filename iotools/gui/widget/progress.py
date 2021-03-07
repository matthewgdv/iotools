from __future__ import annotations

from typing import Any

from PySide6 import QtWidgets

from .base import WidgetHandler


class ProgressBar(WidgetHandler):
    """A manager class for a simple ProgressBar widget which can display and update a progress bar."""

    def __init__(self, length: int = None):
        super().__init__()
        self.widget = QtWidgets.QProgressBar()
        self.widget.setRange(0, length)

    def _get_state(self) -> int:
        return self.widget.value()

    def _set_state(self, val: Any) -> Any:
        self.widget.setValue(val)
