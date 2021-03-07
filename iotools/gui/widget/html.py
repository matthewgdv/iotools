from __future__ import annotations

from PySide6 import QtWidgets

from .base import WidgetHandler


class HtmlDisplay(WidgetHandler):
    """A manager class for a simple HtmlDisplay widget which can render an HTML string."""

    def __init__(self, text: str = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QTextBrowser()
        self.text = text

    def _configure(self) -> None:
        self.widget.setFixedSize(1000, 600)

    def _get_state(self) -> str:
        return self.widget.toHtml()

    def _set_state(self, val: str) -> None:
        self.widget.setHtml(val)

    def _get_text(self) -> str:
        return self.widget.toHtml()

    def _set_text(self, val: str) -> None:
        self.widget.setHtml(val)
