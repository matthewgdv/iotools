from __future__ import annotations

from typing import Any, Tuple, Type, Optional, TYPE_CHECKING

from PySide6 import QtWidgets

from miscutils import PostInitMeta, ReprMixin


if TYPE_CHECKING:
    from iotools.command.argument import Argument


if TYPE_CHECKING:
    from iotools import Gui


class WidgetHandler(ReprMixin, metaclass=PostInitMeta):
    """An abstract widget manager class for concrete widgets to inherit from which guarantees a consistent interface for handling widgets, abstracting away the PyQt5 internals."""
    _registry: dict[QtWidgets.QWidget, WidgetHandler] = {}
    _argument_class: Type[Argument] = None

    def __init__(self) -> None:
        self.widget: Optional[QtWidgets.QWidget] = None
        self.layout: Optional[QtWidgets.QLayout] = None

        self.children: list[WidgetHandler] = []
        self._parent: Any = None

        self._argument: Optional[Argument] = None

    def __post_init__(self) -> None:
        if self.widget is None:
            raise RuntimeError(f"Must assign a Qt Widget as {type(self).__name__}.widget in {type(self).__name__}.{type(self).__init__.__name__}.")

        self._registry[self.widget] = self
        self._configure()

    def __repr__(self) -> str:
        return f"""{type(self).__name__}(parent={self._parent}, children={f"[{', '.join([str(child) for child in self.children])}]" if self.children else None})"""

    def __str__(self) -> str:
        return type(self).__name__

    def __enter__(self) -> WidgetHandler:
        from iotools import Gui
        Gui._stack.append(self)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        from iotools import Gui
        Gui._stack.pop(-1)

    @property
    def state(self) -> Any:
        """A property controlling the state of the widget, e.g. a bool for a checkbox widget, a string for a textedit widget etc."""
        if self.argument is None:
            return self._get_state()
        else:
            self.argument.value = state = self._get_state()
            return state

    @state.setter
    def state(self, val: Any) -> None:
        self._set_state(val)

    @property
    def text(self) -> Any:
        """A property controlling the text displayed on the widget. For some widgets this may be the same as their state (e.g. Label), and some may not have any text at all."""
        return self._get_text()

    @text.setter
    def text(self, val: Any) -> None:
        self._set_text(str(val))

    @property
    def active(self) -> bool:
        """A property controlling the activity status of the widget. When set to False, the widget will be disabled (greyed out and uninteractible)."""
        return self.widget.isEnabled()

    @active.setter
    def active(self, val: bool) -> None:
        self.widget.setEnabled(val)

    @property
    def tooltip(self) -> str:
        return self.widget.toolTip()

    @tooltip.setter
    def tooltip(self, val: str) -> None:
        self.widget.setToolTip(f"{val or ''}\n\n{self._usage_info()}".strip())

    @property
    def parent(self) -> WidgetHandler:
        """A property controlling the parent of the widget. When set, both objects acquire references to one another, and the child attaches to the parent graphically."""
        return self._parent

    @parent.setter
    def parent(self, parent: WidgetHandler) -> None:
        self._set_parent(parent)

    @property
    def argument(self) -> Argument:
        """A property controlling the (optional) argument associated with the widget."""
        return self._argument

    @argument.setter
    def argument(self, argument: Argument) -> None:
        if not isinstance(argument, self._argument_class):
            raise TypeError(f"Cannot add an argument of type {type(argument).__name__} to {type(self).__name__}, must be {self._argument_class.__name__}")

        self._argument = argument

        if argument.info:
            self.tooltip = argument.info

    def stack(self) -> WidgetHandler:
        """Stack this widget onto the last widget or gui element within context (setting it to be this object's parent). If there are none in scope, this will raise IndexError."""
        from iotools import Gui
        self._set_parent(Gui._stack[-1])
        return self

    def grid(self, x: int, y: int) -> WidgetHandler:
        """Insert this widget into the last widget or gui element within context at the given coordinates (setting it to be this object's parent). If there are none in scope, this will raise IndexError."""
        from iotools import Gui
        self._set_parent(parent=Gui._stack[-1], coordinates=(x, y))
        return self

    def toggle_active(self) -> None:
        self.active = not self.active

    def with_argument(self, argument: Argument) -> WidgetHandler:
        self.argument = argument
        return self

    def _configure(self) -> None:
        pass

    def _get_state(self) -> Any:
        raise NotImplementedError

    def _set_state(self, val: Any) -> None:
        raise NotImplementedError

    def _get_text(self) -> str:
        raise NotImplementedError

    def _set_text(self, val: str) -> None:
        raise NotImplementedError

    def _usage_info(self) -> str:
        return ""

    def _set_parent(self, parent: WidgetHandler, coordinates: Tuple[int, int] = None) -> None:
        self._set_parent_handler(parent=parent)
        self._set_parent_widget(parent=parent, coordinates=coordinates)

    def _set_parent_handler(self, parent: WidgetHandler) -> None:
        if self.parent is not None and self in self.parent.children:
            self.parent.children.remove(self)

        self._parent = parent
        parent.children.append(self)

    # noinspection PyArgumentList
    def _set_parent_widget(self, parent: WidgetHandler, coordinates: Tuple[int, int] = None) -> None:
        self.widget.setParent(self.parent.widget)

        if coordinates is None:
            self.parent.layout.addWidget(self.widget)
        else:
            x, y = coordinates
            self.parent.layout.addWidget(self.widget, x, y)
