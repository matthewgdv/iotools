from __future__ import annotations

import sys
from typing import Any, List, Collection

from PyQt5 import QtWidgets as Qwidgets
from PyQt5 import QtCore as Qcore

from miscutils import is_running_in_ipython

from ..widget.widget import Label, Button, HtmlDisplay, ProgressBar, WidgetManager, WidgetManagerFrame, MainWindow

# TODO: replace all instances of addWidget with assignment to parent property


class Gui(Qcore.QObject):
    app, stack = Qwidgets.QApplication([]), []

    def __init__(self, name: str = None):
        super().__init__()
        self.children: List[WidgetManager] = []
        self.window = MainWindow()

        if name is not None:
            self.app.setApplicationName(name), self.app.setApplicationDisplayName(name)

    def __enter__(self) -> Gui:
        Gui.stack.append(self.window)
        return self.window

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        Gui.stack.pop(-1)

    def start_loop(self) -> None:
        self.window.show()
        self.app.exec()

    def end_loop(self) -> None:
        self.window.hide()
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
        with self.window:
            self.title, self.main, self.buttons = WidgetManagerFrame(horizontal=True).stack(), WidgetManagerFrame(horizontal=False, scrollable=True).stack(), WidgetManagerFrame(horizontal=True).stack()


class HtmlGui(Gui):
    def __init__(self, name: str = None, text: str = None) -> None:
        super().__init__(name=name)
        with self:
            self.html, self.button = HtmlDisplay(text=text).stack(), Button(text="continue", command=self.end_loop).stack()

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
