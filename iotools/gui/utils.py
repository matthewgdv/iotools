from __future__ import annotations

from typing import Any, TYPE_CHECKING

from PyQt5 import QtWidgets as Qwidgets

if TYPE_CHECKING:
    from .gui import Gui


class MakeScrollable:
    def __init__(self, container: Qwidgets.QWidget, layout: Qwidgets.QLayout) -> None:
        self.container, self.layout = container, layout

        self.child = Qwidgets.QFrame()
        self.child.setLayout(self.layout)

        scroll_area = Qwidgets.QScrollArea()
        scroll_area.setFrameShape(Qwidgets.QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.child)
        inner_height = self.child.sizeHint().height()
        scroll_area.setMinimumHeight(inner_height if inner_height < 550 else 550)
        scroll_area.setSizePolicy(Qwidgets.QSizePolicy.Preferred, Qwidgets.QSizePolicy.Preferred)

        container_layout = Qwidgets.QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)

        self.container.setLayout(container_layout)


class MainWindow(Qwidgets.QWidget):
    def __init__(self, *args: Any, parent: Gui = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.parent = parent

    def closeEvent(self, event: Any) -> None:
        self.parent.kill()
