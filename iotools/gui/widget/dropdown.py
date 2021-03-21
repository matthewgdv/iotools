from __future__ import annotations

from typing import Any

from PySide6 import QtWidgets

from iotools.command.argument import StringArgument, EnumArgument

from .base import WidgetHandler


class DropDown(WidgetHandler):
    """A manager class for a simple DropDown widget which can display several options."""
    _argument_class = (StringArgument, EnumArgument)

    def __init__(self, choices: list = None, state: str = None, **kwargs: Any) -> None:
        super().__init__()
        self.widget = QtWidgets.QComboBox()

        self._choice_mappings: dict[str, Any] = {}

        self.choices = choices
        self.state = state

    @property
    def choices(self) -> list[str]:
        return [self.widget.itemText(index) for index in range(self.widget.count())]

    @choices.setter
    def choices(self, val: list) -> None:
        self._choice_mappings = {str(choice): choice for choice in val}

        self.widget.clear()
        self.widget.insertItems(0, list(self._choice_mappings))

    def _get_state(self) -> Any:
        return self._choice_mappings[self.widget.currentText()]

    def _set_state(self, val: Any) -> None:
        self.widget.setCurrentText(str(val or ""))
