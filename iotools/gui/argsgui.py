from __future__ import annotations

import datetime as dt
from typing import Dict, List, Any, TYPE_CHECKING

import pandas as pd
from PyQt5 import QtWidgets

from subtypes import DateTime, Frame
from pathmagic import File, Dir
from miscutils import issubclass_safe

from .gui import FormGui
from ..widget.widget import WidgetManager, Button, Label, DropDown, Checkbox, CheckBar, Entry, Text, DateTimeEdit, Table, Calendar, ListTable, DictTable, FileSelect, DirSelect
from ..validator.validator import Validator

if TYPE_CHECKING:
    from ..iohandler import IOHandler, Argument


class WidgetFrame(WidgetManager):
    def __init__(self, argument: Argument, manager: WidgetManager) -> None:
        super().__init__()

        self.arg, self.manager = argument, manager
        self.widget, self.layout = QtWidgets.QGroupBox(), QtWidgets.QHBoxLayout()

        self.make_label()
        self.make_widget()
        if self.arg.nullable:
            self.make_toggle()

    def make_label(self) -> None:
        self.widget.setTitle(self.arg.name)
        self.widget.setToolTip(self.arg.info)

    def make_widget(self) -> None:
        self.manager.parent = self
        self.widget.setLayout(self.layout)

    def make_toggle(self) -> None:
        self.widget.setCheckable(True)
        self.widget.setChecked(False if self.arg.default is None else True)

    @property
    def state(self) -> Any:
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
    def from_arg(cls, arg: Argument) -> WidgetFrame:
        list_like = (list, tuple, set)
        dtype = arg.argtype.dtype if issubclass_safe(arg.argtype, Validator) else arg.argtype

        if arg.choices is not None:
            return WidgetFrame(argument=arg, manager=DropDown(choices=arg.choices, state=arg.default))
        elif dtype is dict and arg.argtype._default_generic_type == (str, bool):
            return WidgetFrame(argument=arg, manager=CheckBar(choices=arg.default))
        elif dtype is bool:
            return WidgetFrame(argument=arg, manager=Checkbox(text=arg.name, state=arg.default))
        elif dtype in {int, float}:
            return WidgetFrame(argument=arg, manager=Entry(state=arg.default))
        elif dtype in {File, Dir}:
            return WidgetFrame(argument=arg, manager=(FileSelect if arg.argtype is File else DirSelect)(state=arg.default))
        elif dtype in {dt.date, dt.datetime, DateTime}:
            return WidgetFrame(argument=arg, manager=DateTimeEdit(state=arg.default, magnitude=arg.magnitude) if arg.magnitude else Calendar(state=arg.default))
        elif dtype is str or dtype is None:
            return WidgetFrame(argument=arg, manager=Text(state=arg.default, magnitude=arg.magnitude))
        elif dtype in {pd.DataFrame, Frame}:
            return WidgetFrame(argument=arg, manager=Table(state=arg.default))
        elif dtype in list_like:
            return WidgetFrame(argument=arg, manager=ListTable(state=arg.default))
        elif dtype is dict:
            return WidgetFrame(argument=arg, manager=DictTable(state=arg.default))
        else:
            raise TypeError(f"Don't know how to handle type: '{arg.argtype}'.")


class ArgsGui:
    """A class that dynamically generates an argument selection GUI upon instantiation, given an IOHandler."""

    def __init__(self, handler: IOHandler) -> None:
        self.handler, self.gui = handler, FormGui(name=handler.app_name)

        with self.gui:
            self.populate_title_segment()
            self.populate_main_segment()
            self.populate_button_segment()

    def populate_title_segment(self) -> None:
        self.gui.title_layout.addWidget(Label(text=self.handler.app_desc).widget)

    def populate_main_segment(self) -> None:
        for arg in self.handler.arguments:
            frame = WidgetFrame.from_arg(arg)
            arg._widget = frame
            self.gui.main_layout.addWidget(frame.widget)

    def populate_button_segment(self) -> None:
        self.gui.button_layout.addWidget(Button(text='Latest Config', command=self.fetch_latest).widget)
        self.gui.button_layout.addWidget(Button(text='Default Config', command=self.fetch_default).widget)
        self.gui.button_layout.addStretch()

        validation = Label(text="Not yet validated.")
        self.gui.button_layout.addWidget(validation.widget)

        self.gui.button_layout.addStretch()
        self.gui.button_layout.addWidget(Button(text='Validate', command=lambda: self.validate_states(validation)).widget)
        self.gui.button_layout.addWidget(Button(text='Proceed', command=self.try_to_proceed).widget)

    def synchronize_states(self) -> List[str]:
        warnings = []
        for arg in self.handler.arguments:
            try:
                arg.value = arg._widget.state
            except Exception as ex:
                warnings.append(f"WARNING ({arg}): {ex}")
        return warnings

    def validate_states(self, label: Label) -> None:
        warnings = self.synchronize_states()
        if warnings:
            print("\n".join(warnings), "\n")
            label.state = "Validation Failed!"
            label.widget.setToolTip("\n".join(warnings))
        else:
            print(f"\nVALIDATION PASSED\nThe following arguments will be passed to the program:\n{ {arg.name : arg.value for arg in self.handler.arguments} }\n")
            label.state = "Validation Passed!"
            label.widget.setToolTip("\n".join([f"{arg.name} = {arg.value}" for arg in self.handler.arguments]))

    def fetch_latest(self) -> None:
        try:
            last_config = self.handler._load_latest_input_config()
            for arg in self.handler.arguments:
                arg._widget.state = last_config[arg.name]
        except FileNotFoundError:
            pass

    def fetch_default(self) -> None:
        for arg in self.handler.arguments:
            arg._widget.state = arg.default

    def try_to_proceed(self) -> None:
        warnings = self.synchronize_states()
        if warnings:
            print("\nERROR: Cannot proceed until the following warnings have been resolved:")
            print("\n".join(warnings), "\n")
        else:
            print(f"\nPROCEEDING\nThe following arguments will be passed to the program:\n{ {arg.name : arg.value for arg in self.handler.arguments} }\n")
            for arg in self.handler.arguments:
                arg._widget = None
            self.gui.end_loop()
