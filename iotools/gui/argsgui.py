from __future__ import annotations

from typing import Any, TYPE_CHECKING, Optional

from .gui import ThreePartGui
from .widget.base import WidgetHandler
from .widget.button import Button
from .widget.label import Label
from .widget.group_box import HorizontalGroupBox

from iotools.misc import Console

if TYPE_CHECKING:
    from iotools.command.declarative import CommandHandler
    from iotools.command.argument import Argument
    from iotools.command.hierarchy import Hierarchy, Node


class ArgsGui(ThreePartGui):
    """A class that dynamically generates an argument selection GUI upon instantiation, given an CommandHandler."""

    def __init__(self, hierarchy: Hierarchy, args: dict = None, handler: CommandHandler = None) -> None:
        super().__init__(name=hierarchy.root.handler.name)
        self.hierarchy = hierarchy
        self.node: Optional[Node] = None

        self.populate_top_segment()
        self.populate_main_segment(args=args, handler=handler)
        self.populate_bottom_segment()

        Console.print_sep("", start_lines=2, start_padding="\n", prefix="", suffix="", end="", stop_sep=False)

    def populate_top_segment(self) -> None:
        """Add widget(s) to the title segment."""

        with self.top:
            Label(text=self.hierarchy.root.handler.desc).stack()

    def populate_main_segment(self, args: dict, handler: CommandHandler) -> None:
        """Add tabs to the main segment and then widget(s) to each of those tabs."""

        with self.main:
            self.hierarchy.create_widgets_recursively()

        if handler is not None:
            self.hierarchy.set_active_tabs_from_handler_ascending(handler=handler)

        if args is not None:
            self.hierarchy.set_widgets_from_namespace_recursively(namespace=args)

    def populate_bottom_segment(self) -> None:
        """Add widget(s) to the button segment."""

        with self.bottom:
            Button(text='Latest Config', command=self.hierarchy.set_widgets_from_last_config_at_current_node).stack()
            Button(text='Default Config', command=self.hierarchy.set_widgets_to_defaults_from_current_node_ascending).stack()

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
            self.hierarchy.clear_widget_references_recursively()
            self.end()

    def set_arguments_from_widgets(self) -> bool:
        """Set the value of the handler's arguments with the state of their widgets, producing warnings for any exceptions that occur."""

        warnings = self.hierarchy.current_node.set_values_from_widgets_catching_errors_as_warnings_ascending()

        if warnings:
            Console.print_sep("\n".join(warnings), start_sep=False, stop_length=75)
            self.validation_label.state = "Validation Failed!"
            self.validation_label.widget.setToolTip("\n".join(warnings))

            return False
        else:
            self.node = self.hierarchy.current_node
            namespace = self.node.get_namespace_ascending()
            dotted_path = ".".join(node.handler.name for node in self.node.get_topdown_hierarchy_ascending())
            Console.print_sep(f"VALIDATION PASSED\nThe following arguments will be passed to '{dotted_path}':\n{namespace}", start_sep=False, stop_length=75)

            self.validation_label.state = "Validation Passed!"
            self.validation_label.widget.setToolTip(str(namespace))

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

    # noinspection PyUnresolvedReferences
    @classmethod
    def from_arg(cls, arg: Argument) -> ArgFrame:
        """Create an ArgFrame from the given argument, inferring a WidgetHandler type for it, and setting it up."""
        return cls(argument=arg, handler=Widget.from_argument(arg=arg))
