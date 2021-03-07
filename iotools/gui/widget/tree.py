from __future__ import annotations

from typing import Any

from PySide6 import QtWidgets

from iotools.command.argument import Argument, DictArgument

from .base import WidgetHandler


class Tree(WidgetHandler):
    """A manager class for a simple tabbed page widget which can display multiple frames that can be switched between."""
    _argument_class = DictArgument

    def __init__(self, state: list = None, deep_type: Argument = None):
        super().__init__()

        self.widget = QtWidgets.QTreeWidget()
        self.deep_type = deep_type
        self.state = state

    def _configure(self) -> None:
        pass

    def _create_item_interactively(self, default: Any = None):
        pass

    def _create_item(self, default: Any = None) -> QtWidgets.QTreeWidgetItem:
        pass

    def _get_state(self) -> list:
        pass

    def _set_state(self, val: list) -> None:
        pass

    def _usage_info(self) -> str:
        return "[Tab] - add new list items\n[Del] - delete the current item"
