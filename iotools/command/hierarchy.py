from __future__ import annotations

import sys
from typing import Any, TYPE_CHECKING, cast, Optional

from miscutils import is_running_in_ipython
from subtypes import Dict

from .argparser import ArgParser
from .enums import RunMode

from iotools.misc import LostObject

if TYPE_CHECKING:
    from .declarative import CommandHandler
    from iotools.gui.widget.tab_page import TabPage


class Hierarchy:
    def __init__(self, root_handler: CommandHandler) -> None:
        self.handler_mappings: dict[CommandHandler, Node] = {}
        self.root = Node(root_handler, hierarchy=self)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(root={repr(self.root)})"

    def __getstate__(self) -> dict:
        return {"root": LostObject(self.root)}

    def __setstate__(self, attrs: dict) -> None:
        self.__dict__ = attrs

    @property
    def current_node(self) -> Node:
        return self.root.get_active_child()

    def choose_strategy(self, *args: Any, **kwargs: Any) -> CommandHandler:
        all_kwargs = kwargs
        explicit_none = False

        if len(args) == 0:
            pass
        elif len(args) == 1:
            single_arg, = args

            if single_arg is None:
                explicit_none = True
            elif isinstance(single_arg, dict):
                if overlapping_keys := (set(single_arg) & set(kwargs)):
                    raise ValueError(f"The following arguments were provided twice: {', '.join(overlapping_keys)}")

                all_kwargs |= args
            else:
                raise TypeError(f"May only provide {dict.__name__} or {None}, provided {single_arg}")
        else:
            raise ValueError(f"No more than one positional argument may be provided. Provided {len(args)}:\n\n{args}")

        if self.root.handler.run_mode == RunMode.SMART:
            if explicit_none or all_kwargs or is_running_in_ipython():
                handler_method = self.run_programatically
            else:
                if not sys.argv[1:]:
                    handler_method = self.run_as_gui
                else:
                    handler_method = self.run_from_commandline
        else:
            handler_method = RunMode(self.root.handler.run_mode).map_to({
                RunMode.COMMANDLINE: self.run_from_commandline,
                RunMode.GUI: self.run_as_gui,
                RunMode.PROGRAMMATIC: self.run_programatically,
            })

        node = handler_method(args=all_kwargs)
        node.handler.save_latest_input_config(namespace=node.get_namespace_ascending())

        for node in node.get_topdown_hierarchy_ascending():
            node.handler.post_validate()

        for node in node.get_topdown_hierarchy_ascending():
            if node.handler.callback:
                node.handler.callback()

        return node.handler

    def run_programatically(self, args: dict = None) -> Node:
        node = self.determine_chosen_node(args, strict=True)
        if args:
            node.set_values_from_namespace_ascending(namespace=args)

        # node.validate_argument_dependencies_ascending()
        return node

    def run_as_gui(self, args: dict = None) -> Node:
        from iotools.gui import ArgsGui
        return ArgsGui(hierarchy=self, args=args, handler=self.determine_chosen_node(args, strict=False).handler).start().node

    def run_from_commandline(self, args: dict = None) -> Node:
        self.root.parser = ArgParser(prog=self.root.handler.name, description=self.root.handler.desc, handler=self.root.handler)
        self.root.parser.add_arguments_from_handler()
        self.root.add_subparsers_recursively()

        node = vars(self.root.parser.parse_args()).get("_node_", self.root)
        # node.validate_argument_dependencies_ascending()
        return node

    def determine_chosen_node(self, args: dict, strict: bool) -> Node:
        current_node, current_dict = self.root, args
        while current_node.children:
            subcommands_found = set(current_node.children) & set(current_dict)

            if len(subcommands_found) == 0:
                if strict:
                    raise ValueError(f"Must provide one of the following subcommands to command '{current_node.handler.name}': {', '.join(current_node.children)}")
                else:
                    return current_node
            elif len(subcommands_found) > 1:
                raise ValueError(f"May only provide 1 subcommand for command '{current_node.handler.name}', provided {len(subcommands_found)}: {', '.join(subcommands_found)}")
            else:
                chosen_subcommand, = subcommands_found
                current_node, current_dict = current_node.children[chosen_subcommand], current_dict[chosen_subcommand]

        return current_node

    def create_widgets_recursively(self) -> None:
        self.root.create_widgets_recursively()

    def clear_widget_references_recursively(self) -> None:
        self.root.clear_widget_references_recursively()

    def set_active_tabs_from_handler_ascending(self, handler: CommandHandler) -> None:
        self.handler_mappings[handler].set_active_tabs_ascending()

    def set_widgets_from_last_config_at_current_node(self) -> None:
        """Load the latest valid arguments profile at the current node and set the widgets accordingly."""
        last_config = (current := self.current_node).handler.load_latest_input_config()

        if last_config is not None:
            current.set_widgets_from_namespace_ascending(last_config)

    def set_widgets_to_defaults_from_current_node_ascending(self) -> None:
        """Set all widget states to their argument defaults from this node to the root."""
        self.current_node.set_widgets_to_defaults_ascending()

    def set_widgets_from_namespace_recursively(self, namespace: dict) -> None:
        self.root.set_widgets_from_namespace_recursively(namespace=namespace)


class Node:
    def __init__(self, handler: CommandHandler, hierarchy: Hierarchy, parent: Node = None) -> None:
        self.handler, self.parent, self.children, self.hierarchy = handler, parent, {child.name: Node(handler=child, hierarchy=hierarchy, parent=self) for child in handler.subhandlers}, hierarchy
        self.page: Optional[TabPage] = None
        self.parser: Optional[ArgParser] = None

        self.hierarchy.handler_mappings[self.handler] = self

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={repr(self.handler.name)}, parent={repr(self.parent)}, children=[{', '.join([repr(child) for child in self.children])}])"

    def add_subparsers_recursively(self) -> None:
        if self.children:
            subparsers = self.parser.add_subparsers()
            for name, child in self.children.items():
                child.parser = cast(ArgParser, subparsers.add_parser(name, prog=child.handler.app_name, description=child.handler.desc, handler=child.handler))
                child.parser.add_arguments_from_handler()
                child.parser.set_defaults(_node_=child)
                child.add_subparsers_recursively()

    def create_widgets_recursively(self) -> None:
        from iotools.gui import ArgFrame, widget

        for arg in self.handler.arguments:
            ArgFrame.from_arg(arg).stack()

        if self.children:
            with widget.TabPage(page_names=list(self.children)).stack() as self.page:
                for name, child in self.children.items():
                    with self.page[name]:
                        child.create_widgets_recursively()

    def clear_widget_references_recursively(self) -> None:
        for argument in self.handler.arguments:
            argument.widget = None

        for child in self.children.values():
            child.clear_widget_references_recursively()

    def get_active_child(self) -> Node:
        return self if not self.children else self.children[self.page.state].get_active_child()

    def get_topdown_hierarchy_ascending(self, nodes: list[Node] = None) -> list[Node]:
        nodes = [self] if nodes is None else [self, *nodes]
        return nodes if self.parent is None else self.parent.get_topdown_hierarchy_ascending(nodes=nodes)

    def get_namespace(self) -> Dict:
        return Dict({argument.name: argument.value for argument in self.handler.arguments})

    def get_namespace_ascending(self) -> Dict:
        outer_namespace = namespace = self.hierarchy.root.get_namespace()

        if self is not self.hierarchy.root:
            for node in self.get_topdown_hierarchy_ascending()[1:]:
                namespace[node.handler.name] = node.get_namespace()
                namespace = namespace[node.handler.name]

        return outer_namespace

    def set_values_from_namespace(self, namespace: dict) -> None:
        for argument in self.handler.arguments:
            if argument.name in namespace:
                argument.value = namespace[argument.name]

    def set_values_from_namespace_ascending(self, namespace: dict) -> None:
        self.hierarchy.root.set_values_from_namespace(namespace=namespace)

        if self is not self.hierarchy.root:
            for node in self.get_topdown_hierarchy_ascending()[1:]:
                namespace = namespace[node.handler.name]
                node.set_values_from_namespace(namespace=namespace)

    def set_active_tabs_ascending(self) -> None:
        if self.parent is not None:
            self.parent.page.state = self.handler.name
            self.parent.set_active_tabs_ascending()

    def set_widgets_to_defaults_ascending(self) -> None:
        """Set all widget states to their argument defaults from this node to the root."""
        for argument in self.handler.arguments:
            argument.widget.state = argument.default

        if self.parent is not None:
            self.parent.set_widgets_to_defaults_ascending()

    def set_widgets_from_namespace(self, namespace: dict) -> None:
        for argument in self.handler.arguments:
            if argument.name in namespace:
                argument.widget.state = namespace[argument.name]

    def set_widgets_from_namespace_ascending(self, namespace: dict) -> None:
        self.hierarchy.root.set_widgets_from_namespace(namespace=namespace)

        if self.hierarchy.current_node is not self.hierarchy.root:
            for node in self.get_topdown_hierarchy_ascending()[1:]:
                namespace = namespace[node.handler.name]
                node.set_widgets_from_namespace(namespace=namespace)

    def set_widgets_from_namespace_recursively(self, namespace: dict) -> None:
        self.set_widgets_from_namespace(namespace=namespace)
        for name, child in self.children.items():
            if name in namespace:
                child.set_widgets_from_namespace_recursively(namespace=namespace[name])

    # def validate_argument_dependencies_ascending(self) -> None:
    #     for argument in self.handler.arguments.values():
    #         if argument.dependency is not None:
    #             argument.dependency.validate()
    #
    #     if self.parent is not None:
    #         self.parent.validate_argument_dependencies_ascending()

    def set_values_from_widgets_catching_errors_as_warnings_ascending(self) -> list[str]:
        prefix, warnings = "", []
        for node in self.get_topdown_hierarchy_ascending():
            prefix += f"{'.' if prefix else ''}{node.handler.name}"
            for arg in node.handler.arguments:
                try:
                    arg.value = arg.widget.state
                except Exception as ex:
                    warnings.append(f"WARNING [{prefix}] ({arg.name}) - {ex}")

        return warnings
