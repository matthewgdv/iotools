from __future__ import annotations

import datetime as dt
from typing import Any, TYPE_CHECKING

import pandas as pd
from PyQt5 import QtWidgets

from pathmagic import File, Dir
from miscutils import issubclass_safe, NameSpaceDict

from .gui import FormGui
from .widget import WidgetHandler, Button, Label, DropDown, Checkbox, CheckBar, Entry, Text, DateTimeEdit, Table, Calendar, ListTable, DictTable, FileSelect, DirSelect, TabPage

if TYPE_CHECKING:
    from .iohandler import IOHandler, Argument


class ArgsGui(FormGui):
    """A class that dynamically generates an argument selection GUI upon instantiation, given an IOHandler."""

    def __init__(self, handler: IOHandler, arguments: dict = None, subcommand: str = None) -> None:
        super().__init__(name=handler.app_name)
        self.handler = self.exitpoint = handler

        self.populate_title_segment()
        self.populate_main_segment(arguments, subcommand)
        self.populate_button_segment()

    @property
    def current_command(self) -> IOHandler:
        if not self.handler.subcommands:
            return self.handler
        else:
            command, page = self.handler, self.main.children[-1]
            while isinstance(page, TabPage):
                command = command.subcommands[page.state]
                page = page[page.state].children[-1]

            return command

    def populate_title_segment(self) -> None:
        """Add widget(s) to the title segment."""
        with self.title:
            Label(text=self.handler.app_desc).stack()

    def populate_main_segment(self, arguments: dict, subcommand: IOHandler) -> None:
        """Add tabs to the main segment and then widget(s) to each of those tabs."""
        with self.main:
            self.recursively_stack_widgets(self.handler)

        if subcommand is not None:
            self.set_active_tabs_from_child_to_root(subcommand)

        if arguments is not None:
            self.set_widgets_from_namespace(namespace=arguments)

    def recursively_stack_widgets(self, handler: IOHandler) -> None:
        for arg in handler.arguments.values():
            ArgFrame.from_arg(arg).stack()

        if handler.subcommands:
            with TabPage(page_names=handler.subcommands).stack() as handler.tabs:
                for name, subcommand in handler.subcommands.items():
                    with handler.tabs[name]:
                        self.recursively_stack_widgets(subcommand)

    def set_active_tabs_from_child_to_root(self, handler: IOHandler) -> None:
        hierarchy = handler._hierarchy_from_root()
        for first, second in zip(hierarchy, hierarchy[1:]):
            first.tabs.state = second.name

    def populate_button_segment(self) -> None:
        """Add widget(s) to the button segment."""
        with self.buttons:
            Button(text='Latest Config', command=self.set_widgets_from_last_config).stack()
            Button(text='Default Config', command=self.set_widgets_from_default_config).stack()

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
            self.exitpoint = self.current_command
            self.handler._recursively_clear_widgets()
            self.end_loop()

    def set_arguments_from_widgets(self) -> bool:
        """Set the value of the handler's arguments with the state of their widgets, producing warnings for any exceptions that occur."""

        prefix, warnings = "", []
        for handler in self.current_command._hierarchy_from_root():
            prefix += f"{'.' if prefix else ''}{handler.name}"
            for arg in handler.arguments.values():
                try:
                    arg.value = arg.widget.state
                except Exception as ex:
                    warnings.append(f"WARNING [{prefix}] ({arg}) - {ex}")

        if warnings:
            print("\n".join(warnings), end="\n\n")
            self.validation_label.state = "Validation Failed!"
            self.validation_label.widget.setToolTip("\n".join(warnings))
            return False
        else:
            namespace = self.current_command._namespace_from_root()
            print(f"VALIDATION PASSED\nThe following arguments will be passed to the program:\n{namespace}\n")
            self.validation_label.state = "Validation Passed!"
            self.validation_label.widget.setToolTip(str(namespace))
            return True

    def set_widgets_from_last_config(self) -> None:
        """Load the handler's latest valid arguments profile and set the widgets accordingly."""
        namespace = self.current_command._load_latest_input_config()
        if namespace is not None:
            self.set_widgets_from_namespace(namespace=namespace)

    def set_widgets_from_default_config(self) -> None:
        """Set all widget states to their argument defaults."""
        for handler in self.current_command._hierarchy_from_root():
            for arg in handler.arguments.values():
                arg.widget.state = arg.default

    def set_widgets_from_namespace(self, namespace: NameSpaceDict) -> None:
        hierarchy = self.current_command._hierarchy_from_root()
        for handler in hierarchy:
            if handler is not hierarchy[0] and handler.name in namespace:
                namespace = namespace[handler.name]

            for name, argument in handler.arguments.items():
                if name in namespace:
                    argument.widget.state = namespace[name]


class ArgFrame(WidgetHandler):
    """A Frame widget which accepts an argument and sets up a label and toggle for the given widget."""

    def __init__(self, argument: Argument, manager: WidgetHandler) -> None:
        super().__init__()

        self.arg, self.manager = argument, manager
        self.widget, self.layout = QtWidgets.QGroupBox(), QtWidgets.QHBoxLayout()

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
        """Create an ArgFrame from the given argument, inferring a WidgetHandler type for it, and setting it up."""
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
