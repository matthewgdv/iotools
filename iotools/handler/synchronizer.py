from __future__ import annotations

from typing import Any, List, Dict, Tuple, TYPE_CHECKING, cast, Optional

from subtypes import Dict_

from .argsgui import ArgsGui, ArgFrame
from .argparser import ArgParser
from ..gui.widget import TabPage
from ..misc.serializer import LostObject

if TYPE_CHECKING:
    from .iohandler import IOHandler


class Synchronizer:
    def __init__(self, root_handler: IOHandler) -> None:
        self.handler_mappings: Dict[IOHandler, Node] = {}
        self.root = Node(root_handler, sync=self)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(root={repr(self.root)})"

    def __getstate__(self) -> dict:
        return {"root": LostObject(self.root)}

    def __setstate__(self, attrs: dict) -> None:
        self.__dict__ = attrs

    @property
    def current_node(self) -> Node:
        return self.root.get_active_child()

    def run_programatically(self, values: Dict_, handler: IOHandler = None) -> Tuple[Dict_, IOHandler]:
        node = self.handler_mappings[self.determine_chosen_handler(handler)] if handler is not None else self.root
        if values:
            node.set_values_from_namespace_ascending(namespace=values)

        node.validate_argument_dependencies_ascending()
        return node.get_namespace_ascending(), node.handler

    def run_as_gui(self, values: Dict[str, Any], handler: IOHandler = None) -> Tuple[Dict_, IOHandler]:
        return ArgsGui(sync=self, values=values, handler=self.determine_chosen_handler(handler)).start().output

    def run_from_commandline(self, args: List[str] = None, values: Dict_ = None, handler: IOHandler = None) -> Tuple[Dict_, IOHandler]:
        self.root.parser = ArgParser(prog=self.root.handler.app_name, description=self.root.handler.app_desc, handler=self.root.handler)
        self.root.parser.add_arguments_from_handler()
        self.root.add_subparsers_recursively()

        node = vars(self.root.parser.parse_args() if args is None else self.root.parser.parse_args(args)).get("node", self.root)
        node.validate_argument_dependencies_ascending()
        return node.get_namespace_ascending(), node.handler

    def create_widgets_recursively(self) -> None:
        self.root.create_widgets_recursively()

    def clear_widget_references_recursively(self) -> None:
        self.root.clear_widget_references_recursively()

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

    def set_widgets_from_namespace_recursively(self, namespace: dict) -> None:
        self.root.set_widgets_from_namespace_recursively(namespace=namespace)

    def determine_chosen_handler(self, handler: Any) -> Optional[IOHandler]:
        if handler is None:
            return None

        from .iohandler import IOHandler

        if isinstance(handler, IOHandler):
            return handler
        elif isinstance(handler, str):
            return self.root.handler.subcommands[handler]
        elif isinstance(handler, list):
            node = self.root.handler

            for step in handler:
                node = node.subcommands[step]

            return node
        else:
            return None


class Node:
    def __init__(self, handler: IOHandler, sync: Synchronizer, parent: Node = None) -> None:
        self.handler, self.parent, self.children, self.sync = handler, parent, {name: Node(handler=child, sync=sync, parent=self) for name, child in handler.subcommands.items()}, sync
        self.page: Optional[TabPage] = None
        self.parser: Optional[ArgParser] = None

        self.sync.handler_mappings[self.handler] = self

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={repr(self.handler.name)}, parent={repr(self.parent)}, children=[{', '.join([repr(child) for child in self.children])}])"

    def add_subparsers_recursively(self) -> None:
        if self.children:
            subparsers = self.parser.add_subparsers()
            for name, child in self.children.items():
                child.parser = cast(ArgParser, subparsers.add_parser(name, prog=child.handler.app_name, description=child.handler.app_desc, handler=child.handler))
                child.parser.add_arguments_from_handler()
                child.parser.set_defaults(node=child)
                child.add_subparsers_recursively()

    def create_widgets_recursively(self) -> None:
        for arg in self.handler.arguments.values():
            ArgFrame.from_arg(arg).stack()

        if self.children:
            with TabPage(page_names=list(self.children)).stack() as self.page:
                for name, child in self.children.items():
                    with self.page[name]:
                        child.create_widgets_recursively()

    def clear_widget_references_recursively(self) -> None:
        for argument in self.handler.arguments.values():
            argument.widget = None

        for child in self.children.values():
            child.clear_widget_references_recursively()

    def get_active_child(self) -> Node:
        return self if not self.children else self.children[self.page.state].get_active_child()

    def get_topdown_hierarchy_ascending(self, nodes: List[Node] = None) -> List[Node]:
        nodes = [self] if nodes is None else [self, *nodes]
        return nodes if self.parent is None else self.parent.get_topdown_hierarchy_ascending(nodes=nodes)

    def get_namespace(self) -> Dict_:
        return Dict_({name: argument.value for name, argument in self.handler.arguments.items()})

    def get_namespace_ascending(self) -> Dict_:
        outer_namespace = namespace = self.sync.root.get_namespace()

        if self is not self.sync.root:
            for node in self.get_topdown_hierarchy_ascending()[1:]:
                namespace[node.handler.name] = node.get_namespace()
                namespace = namespace[node.handler.name]

        return outer_namespace

    def set_values_from_namespace(self, namespace: Dict_) -> None:
        for name, argument in self.handler.arguments.items():
            if name in namespace:
                argument.value = namespace[name]

    def set_values_from_namespace_ascending(self, namespace: Dict_) -> None:
        self.sync.root.set_values_from_namespace(namespace=namespace)

        if self is not self.sync.root:
            for node in self.get_topdown_hierarchy_ascending()[1:]:
                namespace = namespace[node.handler.name]
                node.set_values_from_namespace(namespace=namespace)

    def set_active_tabs_ascending(self) -> None:
        if self.parent is not None:
            self.parent.page.state = self.handler.name
            self.parent.set_active_tabs_ascending()

    def set_widgets_to_defaults_ascending(self) -> None:
        """Set all widget states to their argument defaults from this node to the root."""
        for argument in self.handler.arguments.values():
            argument.widget.state = argument.default

        if self.parent is not None:
            self.parent.set_widgets_to_defaults_ascending()

    def set_widgets_from_namespace(self, namespace: dict) -> None:
        for name, argument in self.handler.arguments.items():
            if name in namespace:
                argument.widget.state = namespace[name]

    def set_widgets_from_namespace_ascending(self, namespace: dict) -> None:
        self.sync.root.set_widgets_from_namespace(namespace=namespace)

        if self.sync.current_node is not self.sync.root:
            for node in self.get_topdown_hierarchy_ascending()[1:]:
                namespace = namespace[node.handler.name]
                node.set_widgets_from_namespace(namespace=namespace)

    def set_widgets_from_namespace_recursively(self, namespace: dict) -> None:
        self.set_widgets_from_namespace(namespace=namespace)
        for name, child in self.children.items():
            if name in namespace:
                self.set_widgets_from_namespace_recursively(namespace=namespace[name])

    def validate_argument_dependencies_ascending(self) -> None:
        for argument in self.handler.arguments.values():
            if argument.dependency is not None:
                argument.dependency.validate()

        if self.parent is not None:
            self.parent.validate_argument_dependencies_ascending()

    def set_values_from_widgets_catching_errors_as_warnings_ascending(self) -> List[str]:
        prefix, warnings = "", []
        for node in self.get_topdown_hierarchy_ascending():
            prefix += f"{'.' if prefix else ''}{node.handler.name}"
            for arg in node.handler.arguments.values():
                try:
                    arg.value = arg.widget.state
                except Exception as ex:
                    warnings.append(f"WARNING [{prefix}] ({arg}) - {ex}")

                if arg.dependency is not None:
                    try:
                        arg.dependency.validate()
                    except Exception as ex:
                        warnings.append(f"WARNING [{prefix}] ({arg}) - {ex}")

        return warnings
