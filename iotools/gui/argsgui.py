from __future__ import annotations

import datetime as dt
from typing import Any, Tuple, TYPE_CHECKING, Optional

import pandas as pd

from maybe import Maybe
from subtypes import Dict
from pathmagic import File, Dir
from miscutils import issubclass_safe

from .gui import ThreePartGui
from .widget import WidgetHandler, Button, Label, DropDown, CheckBar, IntEntry, FloatEntry, Text, DateTimeEdit, Table, Calendar, ListTable, DictTable, FileSelect, DirSelect, HorizontalGroupBox

from iotools.misc import Console

if TYPE_CHECKING:
    from iotools.handler import IOHandler, Argument
    from iotools.handler.synchronizer import Synchronizer


class ArgsGui(ThreePartGui):
    """A class that dynamically generates an argument selection GUI upon instantiation, given an IOHandler."""

    def __init__(self, sync: Synchronizer, values: dict = None, handler: IOHandler = None) -> None:
        super().__init__(name=sync.root.handler.app_name)
        self.sync = sync
        self.output: Optional[Tuple[Dict, IOHandler]] = None

        self.populate_top_segment()
        self.populate_main_segment(values=values, handler=handler)
        self.populate_bottom_segment()

        Console.print_sep("", start_lines=2, start_padding="\n", prefix="", suffix="", end="", stop_sep=False)

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

            self.bottom.layout.addStretch()
            self.validation_label = Label(text="Not yet validated").stack()
            self.bottom.layout.addStretch()

            Button(text='Validate', command=self.set_arguments_from_widgets).stack()
            Button(text='Proceed', command=self.try_to_proceed).stack()

    def try_to_proceed(self) -> None:
        """Validate that the widgets are providing valid arguments, set the argument values accordingly, and if valid end the event loop."""

        if not self.set_arguments_from_widgets():
            Console.print_sep("ERROR: Cannot proceed until the warnings have been resolved...", start_sep=False, stop_length=75)
        else:
            Console.print_sep(f"PROCEEDING...", start_sep=False, suffix="\n\n")
            self.sync.clear_widget_references_recursively()
            self.end()

    def set_arguments_from_widgets(self) -> bool:
        """Set the value of the handler's arguments with the state of their widgets, producing warnings for any exceptions that occur."""

        warnings = self.sync.current_node.set_values_from_widgets_catching_errors_as_warnings_ascending()

        if warnings:
            Console.print_sep("\n".join(warnings), start_sep=False, stop_length=75)
            self.validation_label.state = "Validation Failed!"
            self.validation_label.widget.setToolTip("\n".join(warnings))
            return False
        else:
            node = self.sync.current_node
            self.output = node.get_namespace_ascending(), node.handler
            Console.print_sep(f"VALIDATION PASSED\nThe following arguments will be passed to '{self.sync.root.handler.app_name}':\n{self.output[0]}", start_sep=False, stop_length=75)
            self.validation_label.state = "Validation Passed!"
            self.validation_label.widget.setToolTip(str(self.output[0]))
            return True


class ArgFrame(WidgetHandler):
    """A Frame widget which accepts an argument and sets up a label and toggle for the given widget."""

    def __init__(self, argument: Argument, handler: WidgetHandler) -> None:
        super().__init__()

        self.arg, self.handler = argument, handler
        self.box = HorizontalGroupBox(text=self.arg.name, state=None if not self.arg.nullable else self.arg.default is not None)
        self.box.tooltip = self.arg.info

        self.widget = self.box.widget
        self.arg.widget = self

        self.handler.parent = self.box

    @property
    def state(self) -> Any:
        """Get and set the state of the underlying widget."""
        return self.handler.state if self.box.state is None or self.box.state else None

    @state.setter
    def state(self, val: Any) -> None:
        self.handler.state = val
        if self.box.state is not None:
            self.box.state = val is not None

    @classmethod
    def from_arg(cls, arg: Argument) -> ArgFrame:
        """Create an ArgFrame from the given argument, inferring a WidgetHandler type for it, and setting it up."""
        dtype = arg.argtype.dtype

        if arg.choices is not None:
            return cls(argument=arg, handler=DropDown(choices=arg.choices, state=arg.default, **arg.widget_kwargs))
        elif issubclass_safe(dtype, dict) and arg.argtype._default_generic_type == (str, bool):
            return cls(argument=arg, handler=CheckBar(choices=arg.default, **arg.widget_kwargs))
        elif issubclass_safe(dtype, bool):
            return cls(argument=arg, handler=Button(state=Maybe(arg.default).else_(False), **arg.widget_kwargs))
        elif issubclass_safe(dtype, int):
            return cls(argument=arg, handler=IntEntry(state=arg.default, **arg.widget_kwargs))
        elif issubclass_safe(dtype, float):
            return cls(argument=arg, handler=FloatEntry(state=arg.default, **arg.widget_kwargs))
        elif issubclass_safe(dtype, File):
            return cls(argument=arg, handler=FileSelect(state=arg.default, **arg.widget_kwargs))
        elif issubclass_safe(dtype, Dir):
            return cls(argument=arg, handler=DirSelect(state=arg.default, **arg.widget_kwargs))
        elif issubclass_safe(dtype, dt.datetime):
            return cls(argument=arg, handler=DateTimeEdit(state=arg.default, magnitude=arg.magnitude, **arg.widget_kwargs) if arg.magnitude else Calendar(state=arg.default, **arg.widget_kwargs))
        elif issubclass_safe(dtype, dt.date):
            return cls(argument=arg, handler=Calendar(state=arg.default, **arg.widget_kwargs))
        elif issubclass_safe(dtype, str) or dtype is None:
            return cls(argument=arg, handler=Text(state=arg.default, magnitude=arg.magnitude, **arg.widget_kwargs))
        elif issubclass_safe(dtype, pd.DataFrame):
            return cls(argument=arg, handler=Table(state=arg.default, **arg.widget_kwargs))
        elif issubclass_safe(dtype, list):
            return cls(argument=arg, handler=ListTable(state=arg.default, val_dtype=arg.argtype.val_dtype, **arg.widget_kwargs))
        elif issubclass_safe(dtype, dict):
            return cls(argument=arg, handler=DictTable(state=arg.default, key_dtype=arg.argtype.key_dtype, val_dtype=arg.argtype.val_dtype, **arg.widget_kwargs))
        else:
            raise TypeError(f"Don't know how to handle type: '{arg.argtype}'.")
