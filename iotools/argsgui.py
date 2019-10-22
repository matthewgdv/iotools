from __future__ import annotations

import datetime as dt
from typing import Any, List, TYPE_CHECKING

import pandas as pd
from PyQt5 import QtWidgets

from pathmagic import File, Dir
from miscutils import issubclass_safe, NameSpaceDict

from .gui import FormGui, Gui
from .widget import WidgetHandler, Button, Label, DropDown, Checkbox, CheckBar, Entry, Text, DateTimeEdit, Table, Calendar, ListTable, DictTable, FileSelect, DirSelect, TabPage, WidgetFrame

if TYPE_CHECKING:
    from .iohandler import IOHandler, Argument


class ArgsGui(FormGui):
    """A class that dynamically generates an argument selection GUI upon instantiation, given an IOHandler."""

    def __init__(self, handler: IOHandler, arguments: dict = None, subcommand: str = None) -> None:
        super().__init__(name=handler.app_name)
        self.handler = handler
        self.sync = Synchronizer(root_handler=self.handler)
        self.exitpoint: Node = None

        self.populate_title_segment()
        self.populate_main_segment(arguments, subcommand)
        self.populate_button_segment()

    def populate_title_segment(self) -> None:
        """Add widget(s) to the title segment."""
        with self.title:
            Label(text=self.handler.app_desc).stack()

    def populate_main_segment(self, arguments: dict, subcommand: IOHandler) -> None:
        """Add tabs to the main segment and then widget(s) to each of those tabs."""
        with self.main:
            self.sync.create_widgets_recursively()

        if subcommand is not None:
            self.sync.set_active_tabs_from_handler_ascending(handler=subcommand)

        if arguments is not None:
            self.sync.set_widgets_from_namespace_recursively(namespace=arguments)

    def populate_button_segment(self) -> None:
        """Add widget(s) to the button segment."""
        with self.buttons:
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
            self.exitpoint = self.sync.current_node
            self.sync.clear_widget_references_recursively()
            self.end_loop()

    def set_arguments_from_widgets(self) -> bool:
        """Set the value of the handler's arguments with the state of their widgets, producing warnings for any exceptions that occur."""

        prefix, warnings = "", []
        for node in self.sync.current_node.get_topdown_hierarchy_ascending():
            prefix += f"{'.' if prefix else ''}{node.handler.name}"
            for arg in node.handler.arguments.values():
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
            namespace = self.sync.current_node.get_namespace_ascending()
            print(f"VALIDATION PASSED\nThe following arguments will be passed to the program:\n{namespace}\n")
            self.validation_label.state = "Validation Passed!"
            self.validation_label.widget.setToolTip(str(namespace))
            return True


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


class Synchronizer:
    def __init__(self, root_handler: IOHandler) -> None:
        self.root = Node(root_handler, sync=self)
        self.handler_mappings = {root_handler: self.root}

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    @property
    def current_node(self) -> Node:
        return self.root.get_active_child()

    def create_widgets_recursively(self) -> None:
        self.root.create_widgets_recursively()

    def set_active_tabs_from_handler_ascending(self, handler: IOHandler) -> None:
        self.handler_mappings[handler].set_active_tabs_ascending()

    def set_widgets_from_last_config_at_current_node(self) -> None:
        """Load the latest valid arguments profile at the current node and set the widgets accordingly."""
        current = self.current_node
        last_config = current.handler._load_latest_input_config()

        if last_config is not None:
            current.set_widgets_from_namespace_ascending(last_config)

    def set_widgets_to_defaults_from_current_node_ascending(self) -> None:
        """Set all widget states to their argument defaults from this node to the root."""
        self.current_node.set_widgets_to_defaults_ascending()

    def set_widgets_from_namespace_recursively(self, namespace: NameSpaceDict) -> None:
        self.root.set_widgets_from_namespace_recursively(namespace=namespace)

    def clear_widget_references_recursively(self) -> None:
        self.root.clear_widget_references_recursively()


class Node:
    def __init__(self, handler: IOHandler, sync: Synchronizer, parent: Node = None) -> None:
        self.handler, self.parent, self.children, self.sync = handler, parent, {child.name: Node(handler=child, sync=sync, parent=self) for child in handler.subcommands.values()}, sync
        self.frame: WidgetFrame = None
        self.page: TabPage = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def create_widgets_recursively(self) -> None:
        self.frame = Gui.stack[-1]
        for arg in self.handler.arguments.values():
            ArgFrame.from_arg(arg).stack()

        if self.children:
            with TabPage(page_names=self.children).stack() as self.page:
                for name, child in self.children.items():
                    with self.page[name]:
                        child.create_widgets_recursively()

    def set_active_tabs_ascending(self) -> None:
        if self.parent is not None:
            self.parent.page.state = self.handler.name
            self.parent.set_active_tabs_ascending()

    def get_active_child(self) -> Node:
        return self if not self.children else self.children[self.page.state].get_active_child()

    def set_widgets_to_defaults_ascending(self) -> None:
        """Set all widget states to their argument defaults from this node to the root."""
        for argument in self.handler.arguments.values():
            argument.widget.state = argument.default

        if self.parent is not None:
            self.parent.set_widgets_to_defaults_ascending()

    def get_namespace(self) -> NameSpaceDict:
        return NameSpaceDict({name: argument.value for name, argument in self.handler.arguments.items()})

    def get_namespace_ascending(self) -> NameSpaceDict:
        outer_namespace = namespace = self.sync.root.get_namespace()

        if self.sync.current_node is not self.sync.root:
            for node in self.get_topdown_hierarchy_ascending()[1:]:
                namespace[node.handler.name] = node.get_namespace()
                namespace = namespace[node.handler.name]

        return outer_namespace

    def set_widgets_from_namespace_ascending(self, namespace: NameSpaceDict) -> None:
        self.sync.root.set_widgets_from_namespace(namespace=namespace)

        if self.sync.current_node is not self.sync.root:
            for node in self.get_topdown_hierarchy_ascending()[1:]:
                namespace = namespace[node.handler.name]
                node.set_widgets_from_namespace(namespace=namespace)

    def set_widgets_from_namespace(self, namespace: NameSpaceDict) -> None:
        for name, argument in self.handler.arguments.items():
            if name in namespace:
                argument.widget.state = namespace[name]

    def set_widgets_from_namespace_recursively(self, namespace: NameSpaceDict) -> None:
        self.set_widgets_from_namespace(namespace=namespace)
        for child in self.children.values():
            self.set_widgets_from_namespace_recursively(namespace=namespace)

    def clear_widget_references_recursively(self) -> None:
        for argument in self.handler.arguments.values():
            argument.widget = None

        for child in self.children.values():
            child.clear_widget_references_recursively()

    def get_topdown_hierarchy_ascending(self, nodes: List[Node] = None) -> List[Node]:
        nodes = [self] if nodes is None else [self, *nodes]
        return nodes if self.parent is None else self.parent.get_topdown_hierarchy_ascending(nodes=nodes)
