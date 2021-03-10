from __future__ import annotations

from typing import Any

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt

from iotools.command.argument import Argument, StringArgument, ListArgument

from .base import WidgetHandler
from .frame import HorizontalFrame
from .checkbox import Checkbox


class List(WidgetHandler):
    """A manager class for a simple tabbed page widget which can display multiple frames that can be switched between."""
    _argument_class = ListArgument

    class Item(HorizontalFrame):
        def __init__(self, state: Any, arg: Argument) -> None:
            from .widget import Widget

            super().__init__(margins=1)

            self.arg = arg
            self.handler = Widget.from_argument(self.arg)
            self.handler.state = state

            self.layout.addSpacing(10)

            with self:
                self.handler.stack()

                if self.arg.nullable:
                    Checkbox(state=True, command=self.handler.toggle_active).stack()

        def _get_state(self) -> Any:
            return self.handler.state

        def _set_state(self, val: Any) -> None:
            self.handler.state = val

    def __init__(self, state: list = None, deep_type: Argument = None):
        super().__init__()

        self.widget = QtWidgets.QListWidget()
        self.deep_type = deep_type if deep_type is not None else StringArgument()
        self.state = state

    def _configure(self) -> None:
        self.widget.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.widget.setAlternatingRowColors(True)

        self.delete = QtGui.QShortcut(QtGui.QKeySequence(Qt.Key_Delete), self.widget)
        self.delete.activated.connect(lambda: self.widget.takeItem(self.widget.currentRow()))

        self.tab = QtGui.QShortcut(QtGui.QKeySequence(Qt.Key_Tab), self.widget)
        self.tab.activated.connect(self._create_item_interactively)

    def _create_item_interactively(self, default: Any = None):
        if self.widget.hasFocus():
            self.widget.editItem(self._create_item(default=default))

    def _create_item(self, default: Any = None) -> QtWidgets.QListWidgetItem:
        self.widget.addItem(item := QtWidgets.QListWidgetItem())
        self.widget.setItemWidget(item, widget := self.Item(state=default, arg=self.deep_type).widget)
        item.setSizeHint(widget.sizeHint())

        return item

    def _get_state(self) -> list:
        return [
            self._registry[self.widget.itemWidget(self.widget.item(index))].state
            for index in range(self.widget.count())
        ]

    def _set_state(self, val: list) -> None:
        self.widget.clear()

        if val:
            for element in val:
                self._create_item(default=element)

    def _usage_info(self) -> str:
        return "[Tab] - add new list items\n[Del] - delete the current item"
