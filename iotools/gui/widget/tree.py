from __future__ import annotations

from typing import Any

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt

from iotools.command.argument import Argument, DictionaryArgument

from .base import WidgetHandler
from .frame import HorizontalFrame
from .checkbox import Checkbox


class Tree(WidgetHandler):
    """A manager class for a simple tabbed page widget which can display multiple frames that can be switched between."""
    _argument_class = DictionaryArgument

    class Item(HorizontalFrame):
        def __init__(self, arg: Argument, state: Any = None) -> None:
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

    def __init__(self, state: list = None, key_type: Argument = None, val_type: Argument = None):
        super().__init__()

        self.widget = QtWidgets.QTreeWidget()
        self.key_type, self.val_type = key_type, val_type
        self.state = state

    def _configure(self) -> None:
        self.widget.setHeaderLabels(["key", "value"])
        self.widget.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.widget.setAlternatingRowColors(True)

        self.delete = QtGui.QShortcut(QtGui.QKeySequence(Qt.Key_Delete), self.widget)
        self.delete.activated.connect(lambda: self.widget.takeTopLevelItem(self.widget.currentIndex().row()))

        self.tab = QtGui.QShortcut(QtGui.QKeySequence(Qt.Key_Tab), self.widget)
        self.tab.activated.connect(self._create_item_interactively)

    def _create_item_interactively(self, key: Any = None, val: Any = None):
        if self.widget.hasFocus():
            self.widget.editItem(self._create_item(key, val))

    def _create_item(self, key: Any = None, val: Any = None) -> QtWidgets.QTreeWidgetItem:
        self.widget.addTopLevelItem(item := QtWidgets.QTreeWidgetItem())

        self.widget.setItemWidget(item, 0, key_widget := self.Item(arg=self.key_type, state=key).widget)
        item.setSizeHint(0, key_widget.sizeHint())

        self.widget.setItemWidget(item, 1, val_widget := self.Item(arg=self.val_type, state=val).widget)
        item.setSizeHint(1, val_widget.sizeHint())

        return item

    def _get_state(self) -> dict:
        return {
            self._registry[self.widget.itemWidget(self.widget.topLevelItem(index), 0)].state:
            self._registry[self.widget.itemWidget(self.widget.topLevelItem(index), 1)].state
            for index in range(self.widget.topLevelItemCount())
        }

    def _set_state(self, val: dict) -> None:
        self.widget.clear()

        if val:
            for key, value in val.items():
                self._create_item(key, value)

    def _usage_info(self) -> str:
        return "[Tab] - add new list items\n[Del] - delete the current item"


class TreeWidget(QtWidgets.QTreeWidget):
    def __init__(self):
        super().__init__()
        self._hanging_widgets = None

    def dropEvent(self, event: QtGui.QDropEvent):
        item = self.currentItem()
        key_widget = self.itemWidget(item, 0)
        val_widget = self.itemWidget(item, 1)

        self._hanging_widgets = key_widget, val_widget

        super().dropEvent(event)

        # something goes here

    def on_inserted(self):
        pass
