from __future__ import annotations

from typing import Type

from PySide6 import QtWidgets

from .base import WidgetHandler
from .frame import WidgetFrame, VerticalFrame


class TabPage(WidgetHandler):
    """A manager class for a simple tabbed page widget which can display multiple frames that can be switched between."""

    def __init__(self, page_names: list[str] = None, state: str = None, page_constructor: Type[WidgetFrame] = VerticalFrame):
        super().__init__()

        self.widget, self.page_constructor = QtWidgets.QTabWidget(), page_constructor
        self.pages: dict[str, WidgetFrame] = {}

        for name in page_names:
            self[name] = self.page_constructor()

        if state is not None:
            self.state = state

    def __getitem__(self, key: str) -> WidgetFrame:
        return self.pages[key]

    def __setitem__(self, name: str, val: WidgetFrame) -> None:
        self.pages[name] = val if val is not None else self.page_constructor()
        self.widget.addTab(val.widget, name)

        val._parent = self
        self.children.append(val)

    def __getattr__(self, name: str) -> WidgetFrame:
        if name in self.pages:
            return self.pages[name]
        else:
            raise AttributeError(name)

    def _get_state(self) -> str:
        return self.widget.tabText(self.widget.currentIndex())

    def _set_state(self, val: str) -> None:
        self.widget.setCurrentWidget(self.pages[val].widget)
