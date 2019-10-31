from __future__ import annotations

import datetime as dt
from typing import Any, Tuple, TYPE_CHECKING

import pandas as pd
from PyQt5 import QtWidgets

from maybe import Maybe
from subtypes import NameSpaceDict
from pathmagic import File, Dir
from miscutils import issubclass_safe

from .gui import FormGui
from .widget import WidgetHandler, Button, Label, DropDown, CheckBar, Entry, Text, DateTimeEdit, Table, Calendar, ListTable, DictTable, FileSelect, DirSelect

if TYPE_CHECKING:
    from .iohandler import IOHandler, Argument
    from .synchronizer import Synchronizer


class ArgsGui(FormGui):
    """A class that dynamically generates an argument selection GUI upon instantiation, given an IOHandler."""

    def __init__(self, sync: Synchronizer, values: dict = None, handler: str = None) -> None:
        super().__init__(name=sync.root.handler.app_name)
        self.sync = sync
        self.output: Tuple[NameSpaceDict, IOHandler] = None

        self.populate_top_segment()
        self.populate_main_segment(values=values, handler=handler)
        self.populate_bottom_segment()

    def populate_top_segment(self) -> None:
        """Add widget(s) to the title segment."""
        with self.top:
            Label(text=self.sync.root.handler.app_desc).stack()

    def populate_main_segment(self, values: dict, handler: IOHandler) -> None:
        """Add tabs to the main segment and then widget(s) to each of those tabs."""
        with self.main:
            self.sync.create_widgets_recursively()

        if handler is not None:
            self.sync.set_active_tabs_from_handler_ascending(handler=handler)

        if values is not None:
            self.sync.set_widgets_from_namespace_recursively(namespace=values)

    def populate_bottom_segment(self) -> None:
        """Add widget(s) to the button segment."""
        with self.bottom:
            Button(text='Latest Config', command=self.sync.set_widgets_from_last_config_at_current_node).stack()
            Button(text='Default Config', command=self.sync.set_widgets_to_defaults_from_current_node_ascending).stack()

            self.buttons.layout.addStretch()
            self.validation_label = Label(text="Not yet validated.").stack()
            self.buttons.layout.addStretch()

            Button(text='Validate', command=self.set_arguments_from_widgets).stack()
            Button(text='Proceed', command=self.try_to_proceed).stack()

    def try_to_proceed(self) -> None:
        """Validate that the widgets are providing valid arguments, set the argument values accordingly, and if valid end the event loop."""
        if not self.set_arguments_from_widgets():
            print("ERROR: Cannot proceed until the warnings have been resolved...", end="\n\n")
        else:
            print(f"PROCEEDING...", end="\n\n")
            self.sync.clear_widget_references_recursively()
            self.end_loop()

    def set_arguments_from_widgets(self) -> bool:
        """Set the value of the handler's arguments with the state of their widgets, producing warnings for any exceptions that occur."""

        warnings = self.sync.current_node.set_values_from_widgets_catching_errors_as_warnings_ascending()

        if warnings:
            print("\n".join(warnings), end="\n\n")
            self.validation_label.state = "Validation Failed!"
            self.validation_label.widget.setToolTip("\n".join(warnings))
            return False
        else:
            node = self.sync.current_node
            self.output = node.get_namespace_ascending(), node.handler
            print(f"VALIDATION PASSED\nThe following arguments will be passed to the program:\n{self.output[0]}\n")
            self.validation_label.state = "Validation Passed!"
            self.validation_label.widget.setToolTip(str(self.output[0]))
            return True


class ArgFrame(WidgetHandler):
    """A Frame widget which accepts an argument and sets up a label and toggle for the given widget."""

    def __init__(self, argument: Argument, manager: WidgetHandler) -> None:
        super().__init__()

        self.arg, self.manager = argument, manager

        self.widget, self.layout = QtWidgets.QGroupBox(), QtWidgets.QHBoxLayout()
        self.widget.setLayout(self.layout)

        self.arg.widget = self

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
        """Create an ArgFrame from the given argument, inferring a WidgetHandler type for it, and setting it up."""
        dtype = arg.argtype.dtype

        if arg.choices is not None:
            return ArgFrame(argument=arg, manager=DropDown(choices=arg.choices, state=arg.default))
        elif issubclass_safe(dtype, dict) and arg.argtype._default_generic_type == (str, bool):
            return ArgFrame(argument=arg, manager=CheckBar(choices=arg.default))
        elif issubclass_safe(dtype, bool):
            return ArgFrame(argument=arg, manager=Button(state=Maybe(arg.default).else_(False)))
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
