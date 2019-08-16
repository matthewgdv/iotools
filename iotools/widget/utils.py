from __future__ import annotations

from typing import Any, Callable

from PyQt5 import QtWidgets


class TemporarilyDisconnect:
    def __init__(self, callback: Callable) -> None:
        self.callback = callback

    def from_(self, signal: Any) -> TemporarilyDisconnect:
        self.signal = signal
        return self

    def __enter__(self) -> TemporarilyDisconnect:
        self.signal.disconnect(self.callback)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        self.signal.connect(self.callback)


class MakeScrollable:
    def __init__(self, container: QtWidgets.QWidget, layout: QtWidgets.QLayout) -> None:
        self.container, self.layout = container, layout

        self.child = QtWidgets.QFrame()
        self.child.setLayout(self.layout)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.child)
        inner_height = self.child.sizeHint().height()
        scroll_area.setMinimumHeight(inner_height if inner_height < 550 else 550)
        scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        container_layout = QtWidgets.QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)

        self.container.setLayout(container_layout)
