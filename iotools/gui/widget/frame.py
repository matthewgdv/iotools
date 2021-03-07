from __future__ import annotations

from PySide6 import QtWidgets

from .base import WidgetHandler


class WidgetFrame(WidgetHandler):
    """A manager class for a simple Frame widget which can contain other widgets."""

    layout_constructor = QtWidgets.QGridLayout

    inner_widget: QtWidgets.QFrame
    scroll_area: QtWidgets.QScrollArea
    outer_layout: QtWidgets.QVBoxLayout

    def __init__(self, margins: int = None):
        super().__init__()

        self.widget, self.layout = QtWidgets.QFrame(), self.layout_constructor()

        self.widget.setLayout(self.layout)
        if margins is not None:
            self.layout.setContentsMargins(margins, margins, margins, margins)

    def make_scrollable(self) -> None:
        """Make this frame scrollable if it would be too large to fit normally."""
        self.inner_widget = QtWidgets.QFrame()
        self.inner_widget.setLayout(self.layout)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        self.scroll_area.setWidget(self.inner_widget)

        self.set_scroll_area_dimensions()

        self.outer_layout = QtWidgets.QVBoxLayout()
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.addWidget(self.scroll_area)

        self.widget.setLayout(self.outer_layout)

    def set_scroll_area_dimensions(self, default_pixels: int = 550):
        """Overridable method used to set the scroll area's dimensions."""
        inner_height = self.inner_widget.sizeHint().height()
        self.scroll_area.setMinimumHeight(inner_height if inner_height < default_pixels else default_pixels)


class HorizontalFrame(WidgetFrame):
    layout_constructor = QtWidgets.QHBoxLayout
    layout: QtWidgets.QHBoxLayout


class VerticalFrame(WidgetFrame):
    layout_constructor = QtWidgets.QVBoxLayout
    layout: QtWidgets.QVBoxLayout
