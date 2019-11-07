from __future__ import annotations

import sys
from typing import Any, Type, Collection

from PyQt5 import QtWidgets

from .widget import Label, Button, HtmlDisplay, ProgressBar, WidgetFrame, HorizontalFrame, VerticalFrame


# TODO: Add extra features to Gui (such as menu bar, toolbars, status bar, etc.)


class Gui(QtWidgets.QMainWindow):
    """
    A Gui class that abstracts most of the PyQt5 internals behind a consistent API.
    Widgets can be stacked onto a parent by calling WidgetHandler.stack() while within the context of their parent (a WidgetFrame or a Gui).
    """
    app, stack = QtWidgets.QApplication([]), []

    def __init__(self, name: str = None, central_widget_class: Type[WidgetFrame] = VerticalFrame, kill_on_close: bool = True):
        super().__init__()
        self.kill_on_close = kill_on_close

        self.central = central_widget_class()
        self.central.widget.setParent(self)
        self.setCentralWidget(self.central.widget)

        if name is not None:
            self.setWindowTitle(name), self.app.setApplicationName(name), self.app.setApplicationDisplayName(name)

    def __enter__(self) -> Gui:
        Gui.stack.append(self.central)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        Gui.stack.pop(-1)

    def start(self) -> Gui:
        """Begin the event loop. Will block until 'Gui.end_loop()' is called."""
        self.show()
        self.app.exec()

        return self

    def end(self) -> Gui:
        """End the event loop and resume the execution of the program."""
        self.hide()
        self.app.quit()

        return self

    def closeEvent(self, event: Any) -> None:
        sys.exit() if self.kill_on_close else self.end()


class ThreePartGui(Gui):
    """Gui with 3 separate segments, a top segment, a main segment, and a bottom segment."""

    def __init__(self, name: str = None):
        super().__init__(name=name)
        with self:
            self.top, self.main, self.bottom = HorizontalFrame(margins=0).stack(), VerticalFrame(margins=0).stack(), HorizontalFrame(margins=0).stack()

    def start(self) -> ThreePartGui:
        self.main.make_scrollable()
        super().start()
        return self


class HtmlGui(Gui):
    """Gui designed to render an HTML string in a separate window."""

    def __init__(self, name: str = None, text: str = None) -> None:
        super().__init__(name=name)
        with self:
            self.html, self.button = HtmlDisplay(text=text).stack(), Button(text="continue", command=self.end_loop).stack()


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

    def start(self) -> None:
        raise RuntimeError(f"{type(self).__name__} object does not support the event loop, iterate over it instead.")
