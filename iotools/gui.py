from __future__ import annotations

import sys
from typing import Any, List, Collection

from PyQt5 import QtWidgets

from miscutils import is_running_in_ipython

from .widget import Label, Button, HtmlDisplay, ProgressBar, WidgetHandler, WidgetFrame


class Gui(QtWidgets.QWidget, WidgetHandler):
    """
    A Gui class that abstracts most of the PyQt5 internals behind a consistent API.
    Widgets can be stacked onto a parent by calling WidgetHandler.stack() while within the context of their parent (a WidgetFrame or a Gui).
    """
    app, stack = QtWidgets.QApplication([]), []

    def __init__(self, name: str = None, layout: Any = QtWidgets.QVBoxLayout):
        super().__init__()
        self.children: List[WidgetHandler] = []
        self._parent: WidgetHandler = None

        self.widget, self.layout = self, layout()
        self.widget.setLayout(self.layout)

        if name is not None:
            self.app.setApplicationName(name), self.app.setApplicationDisplayName(name)

    def __enter__(self) -> Gui:
        Gui.stack.append(self)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        Gui.stack.pop(-1)

    def start_loop(self) -> None:
        """Begin the event loop. Will block until 'Gui.end_loop()' is called."""
        self.show()
        self.app.exec()

    def end_loop(self) -> None:
        """End the event loop and resume the execution of the program."""
        self.hide()
        self.app.quit()

    def kill(self) -> None:
        """Exit out of the the current python interpreter. Raises RuntimeError in an interactive IPython session. Automatically called if the Gui quits unexpectedly."""
        if is_running_in_ipython():
            self.app.quit()
            raise RuntimeError("I/O GUI has closed unexpectedly.")
        else:
            sys.exit()

    def closeEvent(self, event: Any) -> None:
        self.kill()


class FormGui(Gui):
    """Gui with 3 separate segments, a title segment, a main segment, and a button segment."""

    def __init__(self, name: str = None):
        super().__init__(name=name)
        with self:
            self.title, self.main, self.buttons = WidgetFrame(horizontal=True).stack(), WidgetFrame(horizontal=False).stack(), WidgetFrame(horizontal=True).stack()

    def start_loop(self):
        self.main.make_scrollable()
        super().start_loop()


class HtmlGui(Gui):
    """Gui designed to render an HTML string in a separate window."""

    def __init__(self, name: str = None, text: str = None) -> None:
        super().__init__(name=name)
        with self:
            self.html, self.button = HtmlDisplay(text=text).stack(), Button(text="continue", command=self.end_loop).stack()

        self.start_loop()


class ProgressBarGui(Gui):
    """
    A wrapper around an iterable that creates a progressbar and updates it as it is iterated over.
    Currently does not work fully asynchronously and will hang noticeably if any steps take longer than a split-second.
    """

    def __init__(self, iterable: Collection[Any], name: str = None, text: str = None) -> None:
        super().__init__(name=name)

        self.iterable, self.count, self.widget = iterable, 0, QtWidgets.QWidget()

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
