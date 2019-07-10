from __future__ import annotations

import sys
from typing import Any, List, Collection

from PyQt5 import QtWidgets as Qwidgets
from PyQt5 import QtCore as Qcore

from miscutils import is_running_in_ipython

from ..widget.widget import Label, Button, HtmlDisplay, ProgressBar, WidgetManager
from .utils import MakeScrollable, MainWindow

# TODO: replace all instances of addWidget with assignment to parent property


class Gui(Qcore.QObject):
    app = Qwidgets.QApplication([])

    def __init__(self, name: str = None):
        super().__init__()
        self.children: List[WidgetManager] = []

        self.widget, self.layout = MainWindow(parent=self), Qwidgets.QVBoxLayout()
        self.widget.setLayout(self.layout)

        if name is not None:
            self.app.setApplicationName(name), self.app.setApplicationDisplayName(name)

    def __enter__(self) -> Gui:
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        if ex_type is None:
            self.start_loop()

    def start_loop(self) -> None:
        self.widget.show()
        self.app.exec()

    def end_loop(self) -> None:
        self.widget.hide()
        self.app.quit()

    def kill(self) -> None:
        if is_running_in_ipython():
            self.app.quit()
            raise RuntimeError("I/O GUI has closed unexpectedly.")
        else:
            sys.exit()


class FormGui(Gui):
    def __init__(self, name: str = None):
        super().__init__(name=name)
        self.title_layout, self.main_layout, self.button_layout = Qwidgets.QHBoxLayout(), Qwidgets.QVBoxLayout(), Qwidgets.QHBoxLayout()

    def start_loop(self) -> None:
        self._set_layout()
        super().start_loop()

    def _set_layout(self) -> None:
        title_segment, main_segment, button_segment = Qwidgets.QGroupBox(), Qwidgets.QGroupBox(), Qwidgets.QGroupBox()
        title_segment.setLayout(self.title_layout), MakeScrollable(container=main_segment, layout=self.main_layout), button_segment.setLayout(self.button_layout)
        self.layout.addWidget(title_segment), self.layout.addWidget(main_segment), self.layout.addWidget(button_segment)


class HtmlGui(Gui):
    def __init__(self, name: str = None, text: str = None) -> None:
        super().__init__(name=name)
        self.text, self.html, self.button = text, HtmlDisplay(text=text), Button(text="continue", command=self.end_loop)
        self.html.parent = self.button.parent = self
        self.start_loop()


class ProgressBarGui(Gui):
    def __init__(self, iterable: Collection[Any], name: str = None, text: str = None) -> None:
        super().__init__(name=name)

        self.iterable, self.count, self.widget = iterable, 0, Qwidgets.QWidget()

        self.label = Label(text=text) if text is not None else None
        self.bar = ProgressBar(length=len(self.iterable))

        if self.label is not None:
            self.label.parent = self
        self.bar.parent = self

    def __iter__(self) -> ProgressBar:
        self.__iter, self.count = iter(self.iterable), 0
        self.bar.state = self.count
        self.widget.show()
        self.app.processEvents()
        return self

    def __next__(self) -> Any:
        self.count += 1
        self.bar.state = self.count
        self.app.processEvents()
        try:
            return next(self.__iter)
        except StopIteration:
            self.widget.hide()
            self.app.quit()
            raise StopIteration

    def start_loop(self) -> None:
        raise RuntimeError(f"{type(self).__name__} object does not support the event loop, iterate over it instead.")
