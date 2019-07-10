from __future__ import annotations

import datetime as dt
import os
from abc import ABC
from typing import Any, Callable, Dict, List, Tuple, Union
import itertools

from PyQt5 import QtCore as QtCore
from PyQt5 import QtWidgets as QtWidgets

from maybe import Maybe
from subtypes import DateTime, Frame
from pathmagic import PathLike, Dir


class WidgetManager(ABC):
    def __init__(self) -> None:
        self.widget = self.get_state = self.set_state = self.get_text = self.set_text = None  # type: Any
        self.children: list = []
        self._parent: Any = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    @property
    def state(self) -> Any:
        return self.get_state()

    @state.setter
    def state(self, val: Any) -> None:
        self.set_state(val)

    @property
    def text(self) -> Any:
        return self.get_text()

    @text.setter
    def text(self, val: Any) -> None:
        self.set_text(val)

    @property
    def active(self) -> bool:
        return self.widget.isEnabled()

    @active.setter
    def active(self, val: bool) -> None:
        self.widget.setEnabled(val)

    @property
    def parent(self) -> Any:
        return self._parent

    @parent.setter
    def parent(self, val: Any) -> None:
        self._parent = val
        val.children.append(self)

        self.parent.layout.addWidget(self.widget)


class WidgetManagerFrame(WidgetManager):
    def __init__(self, horizontal: bool = True):
        super().__init__()

        self.widget, self.layout = QtWidgets.QFrame(), QtWidgets.QHBoxLayout() if horizontal else QtWidgets.QVBoxLayout()

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.widget.setLayout(self.layout)


class Label(WidgetManager):
    def __init__(self, text: str = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QLabel(text or "")
        self.widget.setFrameShape(QtWidgets.QFrame.StyledPanel)

        self.get_text = self.get_state = self.widget.text
        self.set_text = self.set_state = self.widget.setText


class Button(WidgetManager):
    def __init__(self, text: str = None, command: Callable = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QPushButton(text or "")
        self.get_text = self.get_state = self.widget.text
        self.set_text = self.set_state = self.widget.setText

        self.widget.clicked.connect(command)


class Checkbox(WidgetManager):
    def __init__(self, state: bool = False, text: str = None, command: Callable = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QCheckBox(text or "")
        self.get_state, self.set_state = self.widget.isChecked, self.widget.setChecked
        self.get_text, self.set_text = self.widget.text, self.widget.setText

        self.state = Maybe(state).else_(False)
        if command is not None:
            self.widget.clicked.connect(command)


class CheckBar(WidgetManagerFrame):
    """A list of checkboxes placed into a single widget."""

    def __init__(self, choices: Dict[str, bool] = None) -> None:
        super().__init__()

        self.checkboxes = [Checkbox(state=state, text=text) for text, state in choices.items()]

        for checkbox in self.checkboxes:
            checkbox.parent = self

        self.layout.addStretch()

    @property
    def state(self) -> Dict[str, bool]:
        return {checkbox.text: checkbox.state for checkbox in self.checkboxes}

    @state.setter
    def state(self, val: Dict[str, bool]) -> None:
        for checkbox in self.checkboxes:
            checkbox.state = val[checkbox.text]


class DropDown(WidgetManager):
    def __init__(self, choices: List[str] = None, state: str = None) -> None:
        super().__init__()
        self.widget = QtWidgets.QComboBox()
        self.get_state, self.set_state = self.widget.currentText, self.widget.setCurrentText

        self.choices = ["", *choices] if state is None and "" not in choices else choices
        self.state = state

    @property
    def choices(self) -> List[str]:
        return [self.widget.itemText(index) for index in range(self.widget.count())]

    @choices.setter
    def choices(self, val: List[str]) -> None:
        self.widget.clear()
        self.widget.insertItems(0, val)


class Entry(WidgetManager):
    def __init__(self, state: str = None) -> None:
        super().__init__()
        self.widget = QtWidgets.QLineEdit()
        self.get_state, self.set_state = self.widget.text, self.widget.setText

        self.state = state

    @property
    def state(self) -> Any:
        return self.get_state()

    @state.setter
    def state(self, val: Any) -> None:
        self.set_state(str(Maybe(val).else_("")))


class Text(WidgetManager):
    def __init__(self, state: str = None, magnitude: int = 3) -> None:
        super().__init__()

        self.widget = QtWidgets.QTextEdit()
        self.get_state, self.set_state = self.widget.toPlainText, self.widget.setText

        if magnitude is None:
            magnitude = 3

        self.widget.setMaximumHeight(24*magnitude)
        self.state = state

    @property
    def state(self) -> Any:
        return self.get_state()

    @state.setter
    def state(self, val: Any) -> None:
        self.set_state(str(Maybe(val).else_("")))


class PathSelect(WidgetManagerFrame, ABC):
    path_method: Any = None
    prompt: str = None

    def __init__(self, state: PathLike = None, padding: Tuple[int, int] = (10, 5), button_on_left: bool = True) -> None:
        super().__init__(horizontal=True)

        self.button, self.label = Button(text='Browse...', command=self.browse), Label()
        self.button.widget.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.get_state = self.get_text = self.label.get_state
        self.set_state = self.set_text = self.set_path

        self.button.parent = self.label.parent = self

        self.set_path(state)

    def set_path(self, path: PathLike) -> None:
        self.label.set_state(os.fspath(path if path is not None else Dir.from_desktop()))

    def browse(self) -> None:
        path_string = self.text
        starting_dir = Dir.from_desktop() if not path_string else (os.path.dirname(path_string) if os.path.isfile(path_string) else path_string)
        selection = self.path_method(caption=self.prompt, directory=str(starting_dir))
        self.state = selection[0] if isinstance(selection, tuple) else selection


class FileSelect(PathSelect):
    path_method, prompt = staticmethod(QtWidgets.QFileDialog.getOpenFileName), "Select File"


class DirSelect(PathSelect):
    path_method, prompt = staticmethod(QtWidgets.QFileDialog.getExistingDirectory), "Select Dir"


class Calendar(WidgetManager):
    def __init__(self, state: Union[DateTime, dt.date] = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QCalendarWidget()
        self.state = state

    @property
    def state(self) -> DateTime:
        qdate = self.widget.selectedDate()
        return DateTime(qdate.year(), qdate.month(), qdate.day())

    @state.setter
    def state(self, val: Union[DateTime, dt.date]) -> None:
        if val is None:
            val = DateTime.today()

        self.widget.setSelectedDate(QtCore.QDate(val.year, val.month, val.day))


class DateTimeEdit(WidgetManager):
    def __init__(self, state: Union[DateTime, dt.date] = None, magnitude: int = 2) -> None:
        super().__init__()

        self.widget = QtWidgets.QDateTimeEdit()
        self.widget.setDisplayFormat(f"yyyy{'-MM' if magnitude >= 2 else ''}{'-dd' if magnitude >= 3 else ''}{' hh' if magnitude >= 4 else ''}{':mm' if magnitude >= 5 else ''}{':ss' if magnitude >= 6 else ''}")
        self.state = state

    @property
    def state(self) -> DateTime:
        qdate, qtime = self.widget.date(), self.widget.time()
        return DateTime(year=qdate.year(), month=qdate.month(), day=qdate.day(), hour=qtime.hour(), minute=qtime.minute(), second=qtime.second())

    @state.setter
    def state(self, val: Union[DateTime, dt.datetime]) -> None:
        if val is None:
            val = DateTime.now()

        self.widget.setDateTime(QtCore.QDateTime(QtCore.QDate(val.year, val.month, val.day), QtCore.QTime(val.hour, val.minute, val.second)))


class HtmlDisplay(WidgetManager):
    def __init__(self, text: str = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QTextBrowser()
        self.widget.setFixedSize(1000, 600)

        self.get_text = self.get_state = self.widget.toHtml
        self.set_text = self.set_state = self.widget.setHtml

        self.text = text


class ProgressBar(WidgetManager):
    def __init__(self, length: int = None):
        super().__init__()
        self.widget = QtWidgets.QProgressBar()

        self.get_state = self.widget.value
        self.set_state = self.widget.setValue

        self.widget.setRange(0, length)


class Table(WidgetManager):
    TableItem = QtWidgets.QTableWidgetItem

    def __init__(self, state: Frame = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QTableWidget()
        self.widget.currentCellChanged.connect(self.try_extend_table)

        self.state = state

    @property
    def state(self) -> Frame:
        return self.frame

    @state.setter
    def state(self, val: Frame) -> None:
        if val is None:
            val = Frame([(None, None)], columns=["key", "value"])

        self.widget.setColumnCount(len(val.columns))
        self.widget.setRowCount(len(val))
        self.widget.setHorizontalHeaderLabels([str(col) for col in val.columns])

        val = val.fillna_as_none()

        for row_index, sub_dict in enumerate(val.to_dict(orient="records")):
            for col_index, name in enumerate(val.columns):
                self.widget.setItem(row_index, col_index, self.TableItem(str(Maybe(sub_dict[name]).else_(''))))

    @property
    def items(self) -> List[Table.Item]:
        return [self.Item(
                    {self.widget.horizontalHeaderItem(colnum).text(): (Maybe(self.widget.item(rownum, colnum)).text().else_(None))
                     for colnum in range(self.widget.columnCount())}
                ) for rownum in range(self.widget.rowCount())]

    @property
    def frame(self) -> Frame:
        df = Frame.from_objects(self.items)

        invalid_rows = list(itertools.takewhile(lambda row: row[1], reversed([(index, row.isnull().all()) for index, row in df.iterrows()])))
        if invalid_rows:
            df.drop([index for index, isnull in invalid_rows], axis=0, inplace=True)

        return df

    def try_extend_table(self, row: int, col: int, *args: Any) -> None:
        count = self.widget.rowCount()
        if row == count - 1:
            self.widget.insertRow(count)

    class Item:
        def __init__(self, kwargs: Any) -> None:
            for key, val in kwargs.items():
                setattr(self, key, val)

        def __repr__(self) -> str:
            return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"


class ListTable(WidgetManagerFrame):
    def __init__(self, state: list = None) -> None:
        from iohandler import TypeValidator

        super().__init__(horizontal=False)
        self.validator = TypeValidator(dtype=list, optional=True)
        self.table, self.textbox = Table(), Text(magnitude=1)

        self.textbox.widget.textChanged.connect(self.try_interpret_string_as_list)

        self.state = state
        self.textbox.parent = self.table.parent = self

    @property
    def state(self) -> list:
        vals = list(self.table.state.value)
        while vals[-1] is None:
            vals.pop(-1)

        return vals

    @state.setter
    def state(self, val: list) -> None:
        df = Frame([None], columns=["value"]) if val is None else Frame(val, columns=["value"])
        self.table.state = df

    def try_interpret_string_as_list(self) -> None:
        if self.validator.validate(self.textbox.state):
            self.state = self.validator.value


class DictTable(WidgetManagerFrame):
    def __init__(self, state: dict = None) -> None:
        from iohandler import TypeValidator

        super().__init__(horizontal=False)
        self.validator = TypeValidator(dtype=dict, optional=True)
        self.table, self.textbox = Table(), Text(magnitude=1)

        self.textbox.widget.textChanged.connect(self.try_interpret_string_as_dict)

        self.state = state
        self.textbox.parent = self.table.parent = self

    @property
    def state(self) -> dict:
        return {row.key: row.value for row in self.table.state.itertuples() if not (row.key is None and row.value is None)}

    @state.setter
    def state(self, val: dict) -> None:
        df = Frame([(None, None)], columns=["key", "value"]) if val is None else Frame([(key, value) for key, value in val.items()], columns=["key", "value"])
        self.table.state = df

    def try_interpret_string_as_dict(self) -> None:
        if self.validator.validate(self.textbox.state):
            self.state = self.validator.value
