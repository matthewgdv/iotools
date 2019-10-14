from __future__ import annotations

import datetime as dt
from typing import List, Any, TYPE_CHECKING

import pandas as pd
from PyQt5 import QtWidgets

from pathmagic import File, Dir
from miscutils import issubclass_safe

from .gui import FormGui
from .widget import WidgetManager, Button, Label, DropDown, Checkbox, CheckBar, Entry, Text, DateTimeEdit, Table, Calendar, ListTable, DictTable, FileSelect, DirSelect

if TYPE_CHECKING:
    from .iohandler import IOHandler, Argument


class ArgFrame(WidgetManager):
    """A Frame widget which accepts an argument and sets up a label and toggle for the given widget."""

    def __init__(self, argument: Argument, manager: WidgetManager) -> None:
        super().__init__()

        self.arg, self.manager = argument, manager
        self.widget, self.layout = QtWidgets.QGroupBox(), QtWidgets.QHBoxLayout()

        self.make_label()
        self.make_widget()
        if self.arg.nullable:
            self.make_toggle()

    def make_label(self) -> None:
        """Make a label for the argument based on its name and info."""
        self.widget.setTitle(self.arg.name)
        self.widget.setToolTip(self.arg.info)

    def make_widget(self) -> None:
        """Add the widget to the ArgFrame."""
        self.manager.parent = self
        self.widget.setLayout(self.layout)

    def make_toggle(self) -> None:
        """Make the ArgFrame checkable."""
        self.widget.setCheckable(True)
        self.widget.setChecked(False if self.arg.default is None else True)

    @property
    def state(self) -> Any:
        """Get and set the state of the underlying widget."""
        if not self.widget.isCheckable():
            return self.manager.state
        else:
            return self.manager.state if self.widget.isChecked() else None

    @state.setter
    def state(self, val: Any) -> None:
        if not self.widget.isCheckable():
            self.manager.state = val
        else:
            self.manager.state = val
            if val is None:
                self.widget.setChecked(False)
            else:
                self.widget.setChecked(True)

    @classmethod
    def from_arg(cls, arg: Argument) -> ArgFrame:
        """Create an ArgFrame from the given argument, inferring a WidgetManager type for it, and setting it up."""
        dtype = arg.argtype.dtype

        if arg.choices is not None:
            return ArgFrame(argument=arg, manager=DropDown(choices=arg.choices, state=arg.default))
        elif issubclass_safe(dtype, dict) and arg.argtype._default_generic_type == (str, bool):
            return ArgFrame(argument=arg, manager=CheckBar(choices=arg.default))
        elif issubclass_safe(dtype, bool):
            return ArgFrame(argument=arg, manager=Checkbox(text=arg.name, state=arg.default))
        elif issubclass_safe(dtype, int) or issubclass_safe(dtype, float):
            return ArgFrame(argument=arg, manager=Entry(state=arg.default))
        elif issubclass_safe(dtype, File):
            return ArgFrame(argument=arg, manager=FileSelect(state=arg.default))
        elif issubclass_safe(dtype, Dir):
            return ArgFrame(argument=arg, manager=DirSelect(state=arg.default))
        elif issubclass_safe(dtype, dt.date):
            return ArgFrame(argument=arg, manager=DateTimeEdit(state=arg.default, magnitude=arg.magnitude) if arg.magnitude else Calendar(state=arg.default))
        elif issubclass_safe(dtype, str) or dtype is None:
            return ArgFrame(argument=arg, manager=Text(state=arg.default, magnitude=arg.magnitude))
        elif issubclass_safe(dtype, pd.DataFrame):
            return ArgFrame(argument=arg, manager=Table(state=arg.default))
        elif issubclass_safe(dtype, list):
            return ArgFrame(argument=arg, manager=ListTable(state=arg.default, val_dtype=arg.argtype.val_dtype))
        elif issubclass_safe(dtype, dict):
            return ArgFrame(argument=arg, manager=DictTable(state=arg.default, key_dtype=arg.argtype.key_dtype, val_dtype=arg.argtype.val_dtype))
        else:
            raise TypeError(f"Don't know how to handle type: '{arg.argtype}'.")


class ArgsGui(FormGui):
    """A class that dynamically generates an argument selection GUI upon instantiation, given an IOHandler."""

    def __init__(self, handler: IOHandler) -> None:
        super().__init__(name=handler.app_name)
        self.handler = handler

        self.populate_title_segment()
        self.populate_main_segment()
        self.populate_button_segment()

        self.start_loop()

    def populate_title_segment(self) -> None:
        """Add widget(s) to the title segment."""
        with self.title:
            Label(text=self.handler.app_desc).stack()

    def populate_main_segment(self) -> None:
        """Add widget(s) to the main segment."""
        with self.main:
            for arg in self.handler.arguments:
                frame = ArgFrame.from_arg(arg).stack()
                arg._widget = frame

    def populate_button_segment(self) -> None:
        """Add widget(s) to the button segment."""
        with self.buttons:
            Button(text='Latest Config', command=self.fetch_latest).stack()
            Button(text='Default Config', command=self.fetch_default).stack()

            self.buttons.layout.addStretch()
            validation = Label(text="Not yet validated.").stack()
            self.buttons.layout.addStretch()

            Button(text='Validate', command=lambda: self.validate_states(validation)).stack()
            Button(text='Proceed', command=self.try_to_proceed).stack()

    def synchronize_states(self) -> List[str]:
        """Set the value of the handler's arguments with the state of their widgets, producing warnings for any exceptions that occur."""
        warnings = []
        for arg in self.handler.arguments:
            try:
                arg.value = arg._widget.state
            except Exception as ex:
                warnings.append(f"WARNING ({arg}): {ex}")
        return warnings

    def validate_states(self, label: Label) -> None:
        """Validate that all widgets are providing valid inputs to their arguments, and update the gui accordingly."""
        warnings = self.synchronize_states()
        if warnings:
            print("\n".join(warnings), end="\n\n")
            label.state = "Validation Failed!"
            label.widget.setToolTip("\n".join(warnings))
        else:
            print(f"VALIDATION PASSED\nThe following arguments will be passed to the program:\n{ {arg.name : arg.value for arg in self.handler.arguments} }\n")
            label.state = "Validation Passed!"
            label.widget.setToolTip("\n".join([f"{arg.name} = {arg.value}" for arg in self.handler.arguments]))

    def fetch_latest(self) -> None:
        """Load the handler's latest valid arguments profile and set the widgets accordingly."""
        try:
            last_config = self.handler._load_latest_input_config()
            for arg in self.handler.arguments:
                arg._widget.state = last_config[arg.name]
        except FileNotFoundError:
            pass

    def fetch_default(self) -> None:
        """Set all widget states to their argument defaults."""
        for arg in self.handler.arguments:
            arg._widget.state = arg.default

    def try_to_proceed(self) -> None:
        """Validate that the widgets are providing valid arguments, set the argument values accordingly, and if valid end the event loop."""
        warnings = self.synchronize_states()
        if warnings:
            print("ERROR: Cannot proceed until the following warnings have been resolved:")
            print("\n".join(warnings), "\n")
        else:
            print(f"PROCEEDING\nThe following arguments will be passed to the program:\n{ {arg.name : arg.value for arg in self.handler.arguments} }\n")
            for arg in self.handler.arguments:
                arg._widget = None
            self.end_loop()
