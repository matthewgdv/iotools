from __future__ import annotations

import datetime as dt
from typing import Dict, List, Any

import pandas as pd

from subtypes import DateTime, Frame
from pathmagic import File, Dir
from easygui import FormGui, Button, Label, DropDown, Checkbox, CheckBar, Entry, Text, DateTimeEdit, Table, Calendar, ListTable, DictTable, FileSelect, DirSelect
from easygui.widget import WidgetManager
from PyQt5 import QtWidgets

from .iohandler import IOHandler, Argument


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


class WidgetSelector:
    list_like = {list, tuple, set}

    def __init__(self, arg: Argument) -> None:
        self.arg = arg

        if self.arg.choices is not None:
            self.frame = WidgetFrame(argument=self.arg, manager=DropDown(choices=self.arg.choices, state=self.arg.default))
        elif self.arg.argtype is Dict[str, bool]:
            self.frame = WidgetFrame(argument=self.arg, manager=CheckBar(choices=self.arg.default))
        elif self.arg.argtype is bool:
            self.frame = WidgetFrame(argument=self.arg, manager=Checkbox(text=self.arg.name, state=self.arg.default))
        elif self.arg.argtype in {int, float}:
            self.frame = WidgetFrame(argument=self.arg, manager=Entry(state=self.arg.default))
        elif self.arg.argtype in [File, Dir]:
            self.frame = WidgetFrame(argument=self.arg, manager=(FileSelect if self.arg.argtype is File else DirSelect)(state=self.arg.default))
        elif self.arg.argtype in [dt.date, dt.datetime, DateTime]:
            self.frame = WidgetFrame(argument=self.arg, manager=DateTimeEdit(state=self.arg.default, magnitude=self.arg.magnitude) if self.arg.magnitude else Calendar(state=self.arg.default))
        elif self.arg.argtype is str or self.arg.argtype is None:
            self.frame = WidgetFrame(argument=self.arg, manager=Text(state=self.arg.default, magnitude=self.arg.magnitude))
        elif self.arg.argtype in [pd.DataFrame, Frame]:
            self.frame = WidgetFrame(argument=self.arg, manager=Table(state=self.arg.default))
        elif self.arg.argtype in self.list_like or (self.arg.argtype.__module__ == "typing" and self.arg.argtype.__origin__ in self.list_like):
            self.frame = WidgetFrame(argument=self.arg, manager=ListTable(state=self.arg.default))
        elif self.arg.argtype is dict or (self.arg.argtype.__module__ == "typing" and self.arg.argtype.__origin__ is dict):
            self.frame = WidgetFrame(argument=self.arg, manager=DictTable(state=self.arg.default))
        else:
            raise TypeError(f"Don't know how to handle type: '{self.arg.argtype}'.")


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
            frame = WidgetSelector(arg=arg).frame
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
