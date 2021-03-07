from __future__ import annotations

from typing import Union

from PySide6 import QtWidgets

from maybe import Maybe

from iotools.command.argument import IntegerArgument, FloatArgument

from .base import WidgetHandler


class NumericEntry(WidgetHandler):
    """An abstract manager class for a simple numeric SpinBox widget which directs the user to enter a numeral."""
    widget_constructor = None

    def __init__(self, state: str = None, step: int = 1, minimum: int = -2**30, maximum: int = 2**30, prefix: str = None, suffix: str = None) -> None:
        super().__init__()
        self.widget = self.widget_constructor()
        self.widget.setSingleStep(step)

        for argument, callback in [(minimum, self.widget.setMinimum), (maximum, self.widget.setMaximum), (prefix, self.widget.setPrefix), (suffix, self.widget.setSuffix)]:
            if argument is not None:
                callback(argument)

        self.state = state

    def _get_state(self) -> Union[int, float]:
        return self.widget.value()

    def _set_state(self, val: Union[int, float]) -> None:
        self.widget.setValue(Maybe(val).else_(0))


class IntEntry(NumericEntry):
    """A manager class for a simple integer-accepting SpinBox widget which directs the user to enter an integer."""
    _argument_class = IntegerArgument
    widget_constructor = QtWidgets.QSpinBox


class FloatEntry(NumericEntry):
    """A manager class for a simple float-accepting SpinBox widget which directs the user to enter a float."""
    _argument_class = FloatArgument
    widget_constructor = QtWidgets.QDoubleSpinBox
