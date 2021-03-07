from __future__ import annotations

import datetime as dt
from typing import Any, Union

from PySide6 import QtCore, QtWidgets

from subtypes import DateTime, Date

from iotools.command.argument import DateTimeArgument, DateArgument

from .base import WidgetHandler


class Calendar(WidgetHandler):
    """A manager class for a simple Calendar widget which directs the user to select a date."""
    _argument_class = DateArgument

    def __init__(self, state: Union[DateTime, Date] = None, **kwargs: Any) -> None:
        super().__init__()

        self.widget = QtWidgets.QCalendarWidget()
        self.state = state

    def _get_state(self) -> Date:
        qdate = self.widget.selectedDate()
        return Date(qdate.year(), qdate.month(), qdate.day())

    def _set_state(self, val: Union[DateTime, dt.date]) -> None:
        if val is None:
            val = Date.today()

        self.widget.setSelectedDate(QtCore.QDate(val.year, val.month, val.day))


class DateTimeEdit(WidgetHandler):
    """A manager class for a simple DateTimeEdit widget which direct the user to enter a datetime at a level of precision indicated by the magnitude argument."""
    _argument_class = DateTimeArgument

    def __init__(self, state: Union[DateTime, dt.date] = None, magnitude: int = 6, **kwargs: Any) -> None:
        super().__init__()

        self.widget = QtWidgets.QDateTimeEdit()
        self.magnitude = magnitude or 6
        self.state = state

    def _configure(self) -> None:
        self.widget.setDisplayFormat(f"yyyy{'-MM' if self.magnitude >= 2 else ''}{'-dd' if self.magnitude >= 3 else ''}{' hh' if self.magnitude >= 4 else ''}{':mm' if self.magnitude >= 5 else ''}{':ss' if self.magnitude >= 6 else ''}")

    def _get_state(self) -> DateTime:
        qdate, qtime = self.widget.date(), self.widget.time()
        return DateTime(year=qdate.year(), month=qdate.month(), day=qdate.day(), hour=qtime.hour(), minute=qtime.minute(), second=qtime.second())

    def _set_state(self, val: Union[DateTime, dt.datetime]) -> None:
        if val is None:
            val = DateTime.now()

        self.widget.setDateTime(QtCore.QDateTime(QtCore.QDate(val.year, val.month, val.day), QtCore.QTime(val.hour, val.minute, val.second)))
