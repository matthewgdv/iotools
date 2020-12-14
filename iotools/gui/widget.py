from __future__ import annotations

import datetime as dt
import os
from typing import Any, Callable, Dict, List, Tuple, Union, TYPE_CHECKING, Type, Optional
import itertools

from PyQt5 import QtCore
from PyQt5 import QtWidgets

from maybe import Maybe
from subtypes import DateTime, Date, Frame
from pathmagic import PathLike, Dir

from ..misc.validator import Validate, Validator

if TYPE_CHECKING:
    from .gui import Gui
    assert Gui

# TODO: Add email selector WidgetHandler
# TODO: Add ability to expand Table widgets selector WidgetHandler
# TODO: Change widget for list selection to something better than a table


class TemporarilyDisconnect:
    """Utility class used as a context manager to disconnect a callback from a signal and then reconnect it once it drops out of scope."""

    def __init__(self, callback: Callable) -> None:
        self.callback = callback
        self.signal: Any = None

    def from_(self, signal: Any) -> TemporarilyDisconnect:
        """The signal to disconnect the callback from."""
        self.signal = signal
        return self

    def __enter__(self) -> TemporarilyDisconnect:
        self.signal.disconnect(self.callback)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        self.signal.connect(self.callback)


class WidgetHandler:
    """An abstract widget manager class for concrete widgets to inherit from which guarantees a consistent interface for handling widgets, abstracting away the PyQt5 internals."""

    def __init__(self) -> None:
        self.widget: Optional[QtWidgets.QWidget] = None
        self.layout: Optional[QtWidgets.QLayout] = None
        self.get_state = self.set_state = self.get_text = self.set_text = None  # type: Optional[Callable]

        self.children: list[WidgetHandler] = []
        self._parent: Any = None

    def __repr__(self) -> str:
        return f"""{type(self).__name__}(parent={self._parent}, children={f"[{', '.join([str(child) for child in self.children])}]" if self.children else None})"""

    def __str__(self) -> str:
        return type(self).__name__

    def __enter__(self) -> WidgetHandler:
        from .gui import Gui
        Gui.stack.append(self)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        from .gui import Gui
        Gui.stack.pop(-1)

    @property
    def state(self) -> Any:
        """A property controlling the state of the widget, e.g. a bool for a checkbox widget, a string for a textedit widget etc."""
        return self.get_state()

    @state.setter
    def state(self, val: Any) -> None:
        self.set_state(val)

    @property
    def text(self) -> Any:
        """A property controlling the text displayed on the widget. For some widgets this may be the same as their state, and some may not have any text at all."""
        return self.get_text()

    @text.setter
    def text(self, val: Any) -> None:
        self.set_text(val)

    @property
    def active(self) -> bool:
        """A property controlling the activity status of the widget. When set to False, the widget will be disabled (greyed out and uninteractible)."""
        return self.widget.isEnabled()

    @active.setter
    def active(self, val: bool) -> None:
        self.widget.setEnabled(val)

    @property
    def tooltip(self) -> str:
        return self.widget.toolTip()

    @tooltip.setter
    def tooltip(self, val: str) -> None:
        self.widget.setToolTip(val)

    @property
    def parent(self) -> WidgetHandler:
        """A property controlling the parent of the widget. When set, both objects acquire references to one another, and the child attaches to the parent graphically."""
        return self._parent

    @parent.setter
    def parent(self, parent: WidgetHandler) -> None:
        self.set_parent(parent)

    def stack(self) -> WidgetHandler:
        """Stack this widget onto the last widget or gui element within context (setting it to be this object's parent). If there are none in scope, this will raise IndexError."""
        from .gui import Gui
        self.set_parent(Gui.stack[-1])
        return self

    def grid(self, x: int, y: int) -> WidgetHandler:
        """Insert this widget into the last widget or gui element within context at the given coordinates (setting it to be this object's parent). If there are none in scope, this will raise IndexError."""
        from .gui import Gui
        self.set_parent(parent=Gui.stack[-1], coordinates=(x, y))
        return self

    def set_parent(self, parent: WidgetHandler, coordinates: Tuple[int, int] = None) -> None:
        self._set_parent_handler(parent=parent)
        self._set_parent_widget(parent=parent, coordinates=coordinates)

    def _set_parent_handler(self, parent: WidgetHandler) -> None:
        if self.parent is not None and self in self.parent.children:
            self.parent.children.remove(self)

        self._parent = parent
        parent.children.append(self)

    # noinspection PyArgumentList
    def _set_parent_widget(self, parent: WidgetHandler, coordinates: Tuple[int, int] = None) -> None:
        self.widget.setParent(self.parent.widget)

        if coordinates is None:
            self.parent.layout.addWidget(self.widget)
        else:
            x, y = coordinates
            self.parent.layout.addWidget(self.widget, x, y)


class WidgetFrame(WidgetHandler):
    """A manager class for a simple Frame widget which can contain other widgets."""

    layout_constructor = QtWidgets.QGridLayout

    inner_widget: QtWidgets.QFrame
    scroll_area: QtWidgets.QScrollArea
    outer_layout: QtWidgets.QVBoxLayout

    def __init__(self, margins: int = None):
        super().__init__()

        self.widget, self.layout = QtWidgets.QFrame(), self.layout_constructor()

        self.widget.setLayout(self.layout)
        if margins is not None:
            self.layout.setContentsMargins(margins, margins, margins, margins)

    def set_scroll_area_dimensions(self, default_pixels: int = 550):
        """Overridable method used to set the scroll area's dimensions."""
        inner_height = self.inner_widget.sizeHint().height()
        self.scroll_area.setMinimumHeight(inner_height if inner_height < default_pixels else default_pixels)

    def make_scrollable(self) -> None:
        """Make this frame scrollable if it would be too large to fit normally."""
        self.inner_widget = QtWidgets.QFrame()
        self.inner_widget.setLayout(self.layout)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.scroll_area.setWidget(self.inner_widget)

        self.set_scroll_area_dimensions()

        self.outer_layout = QtWidgets.QVBoxLayout()
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.addWidget(self.scroll_area)

        self.widget.setLayout(self.outer_layout)


class HorizontalFrame(WidgetFrame):
    layout_constructor = QtWidgets.QHBoxLayout


class VerticalFrame(WidgetFrame):
    layout_constructor = QtWidgets.QVBoxLayout


class GroupBox(WidgetHandler):
    layout_constructor = QtWidgets.QGridLayout

    def __init__(self, text: str, state: bool = None) -> None:
        super().__init__()

        self.widget, self.layout = QtWidgets.QGroupBox(), self.layout_constructor()
        self.widget.setLayout(self.layout)

        self.get_text, self.set_text = self.widget.title, self.widget.setTitle

        self.text, self.state = text, state

    @property
    def state(self) -> bool:
        return None if not self.widget.isCheckable() else self.widget.isChecked()

    @state.setter
    def state(self, val: bool) -> None:
        self.widget.setCheckable(val is not None)
        if val is not None:
            self.widget.setChecked(val)


class HorizontalGroupBox(GroupBox):
    layout_constructor = QtWidgets.QHBoxLayout


class VerticalGroupBox(GroupBox):
    layout_constructor = QtWidgets.QVBoxLayout


class Label(WidgetHandler):
    """A manager class for a simple Label widget which can display text."""

    def __init__(self, text: str = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QLabel(text or "")
        self.widget.setFrameShape(QtWidgets.QFrame.StyledPanel)

        self.get_text = self.get_state = self.widget.text
        self.set_text = self.set_state = self.widget.setText


class Button(WidgetHandler):
    """A manager class for a simple Button widget which can trigger a callback when pushed."""

    def __init__(self, text: str = None, command: Callable = None, state: bool = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QPushButton(text or "")
        self.get_text, self.set_text = self.widget.text, self.widget.setText
        self.get_state, self.set_state = self.widget.isChecked, self.widget.setChecked

        if state is not None:
            self.widget.setCheckable(True)
            self.state = state

        if command is not None:
            self.widget.clicked.connect(command)


class Checkbox(WidgetHandler):
    """A manager class for a simple Checkbox widget which can be in the checked or unchecked state."""

    _values_to_states = {False: QtCore.Qt.Unchecked, None: QtCore.Qt.PartiallyChecked, True: QtCore.Qt.Checked}
    _states_to_values = {val: key for key, val in _values_to_states.items()}

    def __init__(self, state: bool = False, text: str = None, tristate: bool = False, command: Callable = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QCheckBox(text or "")
        self.get_text, self.set_text = self.widget.text, self.widget.setText
        self.tristate = tristate

        if command is not None:
            self.widget.clicked.connect(command)

        self.state = Maybe(state).else_(False)

    @property
    def state(self) -> bool:
        return self._states_to_values[self.widget.checkState()]

    @state.setter
    def state(self, val: bool) -> None:
        self.widget.setCheckState(self._values_to_states[val]) if self.tristate else self.widget.setChecked(val)

    @property
    def tristate(self) -> bool:
        return self.widget.isTristate()

    @tristate.setter
    def tristate(self, val: bool) -> None:
        return self.widget.setTristate(val)


class CheckBar(HorizontalFrame):
    """A manager class for a list of Checkbox widgets placed into a single widget."""

    def __init__(self, choices: dict[str, bool] = None, **kwargs: Any) -> None:
        super().__init__(margins=0)

        self.checkboxes = [Checkbox(state=state, text=text) for text, state in choices.items()]

        for checkbox in self.checkboxes:
            checkbox.parent = self

        # self.layout.addStretch()

    @property
    def state(self) -> dict[str, bool]:
        return {checkbox.text: checkbox.state for checkbox in self.checkboxes}

    @state.setter
    def state(self, val: dict[str, bool]) -> None:
        for checkbox in self.checkboxes:
            checkbox.state = val[checkbox.text]


class DropDown(WidgetHandler):
    """A manager class for a simple DropDown widget which can display several options."""

    def __init__(self, choices: list[str] = None, state: str = None, **kwargs: Any) -> None:
        super().__init__()
        self.widget = QtWidgets.QComboBox()
        self.get_state, self.set_state = self.widget.currentText, self.widget.setCurrentText

        self.choices = ["", *choices] if state is None and "" not in choices else choices
        self.state = str(state)

    @property
    def choices(self) -> list[str]:
        return [self.widget.itemText(index) for index in range(self.widget.count())]

    @choices.setter
    def choices(self, val: list[str]) -> None:
        self.widget.clear()
        self.widget.insertItems(0, val)


class Entry(WidgetHandler):
    """A manager class for a simple text Entry widget which can capture text."""

    def __init__(self, state: str = None) -> None:
        super().__init__()
        self.widget = QtWidgets.QLineEdit()
        self.state = state

    @property
    def state(self) -> Any:
        return self.widget.text()

    @state.setter
    def state(self, val: Any) -> None:
        self.widget.setText(str(Maybe(val).else_("")))


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

    @property
    def state(self) -> Union[int, float]:
        return self.widget.value()

    @state.setter
    def state(self, val: Any) -> None:
        self.widget.setValue(Maybe(val).else_(0))


class IntEntry(NumericEntry):
    """A manager class for a simple integer-accepting SpinBox widget which directs the user to enter an integer."""
    widget_constructor = QtWidgets.QSpinBox


class FloatEntry(NumericEntry):
    """A manager class for a simple float-accepting SpinBox widget which directs the user to enter a float."""
    widget_constructor = QtWidgets.QDoubleSpinBox


class Text(WidgetHandler):
    """A manager class for a simple text Text widget which can capture text and has editor-like features."""

    def __init__(self, state: str = None, magnitude: int = 3, **kwargs: Any) -> None:
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


class PathSelect(HorizontalFrame):
    """An abstract manager class for a simple PathSelect widget which directs the user to browse for a path."""
    path_method: Any = None
    prompt: str = None

    def __init__(self, state: PathLike = None, padding: Tuple[int, int] = (10, 5), button_on_left: bool = True) -> None:
        super().__init__(margins=0)

        self.button, self.label = Button(text='Browse...', command=self.browse), Label()
        self.button.widget.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.get_state = self.get_text = self.label.get_state
        self.set_state = self.set_text = self.set_path

        self.button.parent = self.label.parent = self

        self.set_path(state)

    def set_path(self, path: PathLike) -> None:
        """Set the widget's state to the given path."""
        self.label.set_state(os.fspath(path if path is not None else Dir.from_desktop()))

    def browse(self) -> None:
        """Open an operating-system specific path entry dialog."""
        path_string = self.text
        starting_dir = Dir.from_desktop() if not path_string else (os.path.dirname(path_string) if os.path.isfile(path_string) else path_string)

        selection = self.path_method(caption=self.prompt, directory=str(starting_dir))

        new_path = selection[0] if isinstance(selection, tuple) else selection
        if new_path:
            self.state = os.path.abspath(new_path)


class FileSelect(PathSelect):
    """A manager class for a simple FileSelect widget which directs the user to browse for a file."""
    path_method, prompt = staticmethod(QtWidgets.QFileDialog.getOpenFileName), "Select File"


class DirSelect(PathSelect):
    """A manager class for a simple DirSelect widget which directs the user to browse for a folder."""
    path_method, prompt = staticmethod(QtWidgets.QFileDialog.getExistingDirectory), "Select Dir"


class Calendar(WidgetHandler):
    """A manager class for a simple Calendar widget which directs the user to select a date."""

    def __init__(self, state: Union[DateTime, Date] = None, **kwargs: Any) -> None:
        super().__init__()

        self.widget = QtWidgets.QCalendarWidget()
        self.state = state

    @property
    def state(self) -> DateTime:
        qdate = self.widget.selectedDate()
        return Date(qdate.year(), qdate.month(), qdate.day())

    @state.setter
    def state(self, val: Union[DateTime, dt.date]) -> None:
        if val is None:
            val = Date.today()

        self.widget.setSelectedDate(QtCore.QDate(val.year, val.month, val.day))


class DateTimeEdit(WidgetHandler):
    """A manager class for a simple DateTimeEdit widget which direct the user to enter a datetime at a level of precision indicated by the magnitude argument."""

    def __init__(self, state: Union[DateTime, dt.date] = None, magnitude: int = 2, **kwargs: Any) -> None:
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


class HtmlDisplay(WidgetHandler):
    """A manager class for a simple HtmlDisplay widget which can render an HTML string."""

    def __init__(self, text: str = None) -> None:
        super().__init__()

        self.widget = QtWidgets.QTextBrowser()
        self.widget.setFixedSize(1000, 600)

        self.get_text = self.get_state = self.widget.toHtml
        self.set_text = self.set_state = self.widget.setHtml

        self.text = text


class ProgressBar(WidgetHandler):
    """A manager class for a simple ProgressBar widget which can display and update a progress bar."""

    def __init__(self, length: int = None):
        super().__init__()
        self.widget = QtWidgets.QProgressBar()

        self.get_state = self.widget.value
        self.set_state = self.widget.setValue

        self.widget.setRange(0, length)


class TabPage(WidgetHandler):
    """A manager class for a simple tabbed page widget which can display multiple frames that can be switched between."""

    def __init__(self, page_names: list[str] = None, state: str = None, page_constructor: Type[WidgetFrame] = VerticalFrame):
        super().__init__()

        self.widget, self.page_constructor = QtWidgets.QTabWidget(), page_constructor
        self.pages: dict[str, WidgetHandler] = {}

        for name in page_names:
            self[name] = self.page_constructor()

        if state is not None:
            self.state = state

    def __getitem__(self, key: str) -> WidgetHandler:
        return self.pages[key]

    def __setitem__(self, name: str, val: WidgetFrame) -> None:
        self.pages[name] = val if val is not None else self.page_constructor()
        self.widget.addTab(val.widget, name)

        val._parent = self
        self.children.append(val)

    def __getattr__(self, name: str) -> WidgetHandler:
        if name in self.pages:
            return self.pages[name]
        else:
            raise AttributeError(name)

    @property
    def state(self) -> str:
        return self.widget.tabText(self.widget.currentIndex())

    @state.setter
    def state(self, val: str) -> None:
        self.widget.setCurrentWidget(self.pages[val].widget)


class Table(WidgetHandler):
    """A manager class for a simple Table widget which can prompt the user to fill out a table."""
    TableItem = QtWidgets.QTableWidgetItem

    def __init__(self, state: Frame = None, **kwargs: Any) -> None:
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
    def items(self) -> list[Table.Item]:
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


class GenericTable(VerticalFrame):
    """An abstract manager class for a Table widget which can validate the typing of its inputs and convert them to python types."""
    validator: Validator
    state: Any

    def __init__(self) -> None:
        super().__init__()

        self.table, self.textbox = Table(), Text(magnitude=1)

        self.textbox.widget.textChanged.connect(self.set_widget_from_textbox)
        self.table.widget.cellChanged.connect(self.set_textbox_from_widget)

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

    def set_widget_from_textbox(self) -> None:
        if self.validator.is_valid(self.textbox.state):
            with TemporarilyDisconnect(self.set_textbox_from_widget).from_(self.table.widget.cellChanged):
                self.state = self.validator.convert(self.textbox.state)

    def set_textbox_from_widget(self, row: int, col: int, *args: Any) -> None:
        if self.validator.is_valid(self.state):
            with TemporarilyDisconnect(self.set_widget_from_textbox).from_(self.textbox.widget.textChanged):
                self.textbox.state = repr(self.validator.convert(self.state))


class ListTable(GenericTable):
    """A manager class for a ListTable widget which can validate (and coerce to a python list) a typed list from a table widget or a textbox."""

    def __init__(self, state: list = None, val_dtype: Any = None, **kwargs: Any) -> None:
        super().__init__()
        self.validator = Validate.List(nullable=True)[val_dtype]
        self.state = state

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


class DictTable(GenericTable):
    """A manager class for a DictTable widget which can validate (and coerce to a python dict) a typed dict from a table widget or a textbox."""

    def __init__(self, state: dict = None, key_dtype: Any = None, val_dtype: Any = None, **kwargs: Any) -> None:
        super().__init__()
        self.validator = Validate.Dict(nullable=True)[key_dtype, val_dtype]
        self.state = state

    @property
    def state(self) -> dict:
        return {row.key: row.value for row in self.table.state.itertuples() if not (row.key is None and row.value is None)}

    @state.setter
    def state(self, val: dict) -> None:
        df = Frame([(None, None)], columns=["key", "value"]) if val is None else Frame([(key, value) for key, value in val.items()], columns=["key", "value"])
        self.table.state = df
