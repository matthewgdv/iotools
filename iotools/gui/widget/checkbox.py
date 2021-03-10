from __future__ import annotations

from typing import Any, Callable

from PySide6 import QtCore, QtWidgets

from maybe import Maybe

from iotools.command.argument import BooleanArgument, DictionaryArgument

from .base import WidgetHandler
from .frame import HorizontalFrame


class Checkbox(WidgetHandler):
    """A manager class for a simple Checkbox widget which can be in the checked or unchecked state."""
    _argument_class = BooleanArgument

    _values_to_states = {True: QtCore.Qt.CheckState.Checked, False: QtCore.Qt.CheckState.Unchecked, None: QtCore.Qt.CheckState.PartiallyChecked}
    _states_to_values = {val: key for key, val in _values_to_states.items()}

    def __init__(self, state: bool = False, text: str = None, tristate: bool = False, command: Callable = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QCheckBox(text or "")
        self.tristate = tristate

        if command is not None:
            self.widget.clicked.connect(command)

        self.state = Maybe(state).else_(False)

    def _configure(self) -> None:
        self.widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)

    @property
    def tristate(self) -> bool:
        return self.widget.isTristate()

    @tristate.setter
    def tristate(self, val: bool) -> None:
        return self.widget.setTristate(val)

    def _get_state(self) -> Any:
        return self._states_to_values[self.widget.checkState()]

    def _set_state(self, val: Any) -> None:
        self.widget.setCheckState(self._values_to_states[val]) if self.tristate else self.widget.setChecked(val if val is not None else False)

    def _get_text(self) -> str:
        return self.widget.text()

    def _set_text(self, val: str) -> None:
        self.widget.setText(val)


class CheckBar(HorizontalFrame):
    """A manager class for a list of Checkbox widgets placed into a single widget."""
    _argument_class = DictionaryArgument

    def __init__(self, choices: dict[str, bool] = None, **kwargs: Any) -> None:
        super().__init__(margins=0)

        self.checkboxes = [Checkbox(state=state, text=text) for text, state in choices.items()]

        for checkbox in self.checkboxes:
            checkbox.parent = self

    def _get_state(self) -> Any:
        return {checkbox.text: checkbox.state for checkbox in self.checkboxes}

    def _set_state(self, val: Any) -> None:
        for checkbox in self.checkboxes:
            checkbox.state = val[checkbox.text]
