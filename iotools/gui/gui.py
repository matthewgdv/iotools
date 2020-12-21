from __future__ import annotations

import sys
import types
from typing import Any, Type, Callable, Collection, cast

from PyQt5 import QtWidgets
from PyQt5 import QtGui

from subtypes import Enum
from pathmagic import File, PathLike

from .widget import Label, Button, HtmlDisplay, ProgressBar, WidgetFrame, HorizontalFrame, VerticalFrame
from iotools import res

# TODO: Add extra features to Gui (such as menu bar, toolbars, status bar, etc.)

res = cast(types.ModuleType, res)


class Gui(QtWidgets.QMainWindow):
    """
    A Gui class that abstracts most of the PyQt5 internals behind a consistent API.
    Widgets can be stacked onto a parent by calling WidgetHandler.stack() while within the context of their parent (a WidgetFrame or a Gui).
    """
    app, stack = QtWidgets.QApplication([]), []

    def __init__(self, name: str = None, central_widget_class: Type[WidgetFrame] = VerticalFrame, on_close: Callable = sys.exit):
        super().__init__()
        self.name, self.on_close = name, on_close or self.end

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
        self.on_close()


class ThreePartGui(Gui):
    """Gui with 3 separate segments, a top segment, a main segment, and a bottom segment."""

    def __init__(self, name: str = None, on_close: Callable = sys.exit):
        super().__init__(name=name, on_close=on_close)
        with self:
            self.top, self.main, self.bottom = HorizontalFrame(margins=0).stack(), VerticalFrame(margins=0).stack(), HorizontalFrame(margins=0).stack()

            vertical_fixed = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
            self.top.widget.setSizePolicy(vertical_fixed), self.bottom.widget.setSizePolicy(vertical_fixed)

    def start(self) -> ThreePartGui:
        self.main.make_scrollable()
        super().start()
        return self


class HtmlGui(Gui):
    """Gui designed to render an HTML string in a separate window."""

    def __init__(self, name: str = None, text: str = None, on_close: Callable = lambda: None) -> None:
        super().__init__(name=name, on_close=on_close)
        with self:
            self.html, self.button = HtmlDisplay(text=text).stack(), Button(text="continue", command=self.end).stack()


class SystemTrayGui(Gui):
    """
        A GUI used for writing long-running system tray applications. Exposes the same high-level API as the Gui class.
        """

    class NotificationLevel(Enum):
        INFO, WARNING, CRITICAL = "info", "warning", "critical"

    notification_mappings = {
        NotificationLevel.INFO: 1,
        NotificationLevel.WARNING: 2,
        NotificationLevel.CRITICAL: 3
    }

    def __init__(self, name: str, hide_option: bool = None) -> None:
        super().__init__(name=name)
        self.hide_option = hide_option

        self.menu = QtWidgets.QMenu(self)

        self.widget = QtWidgets.QSystemTrayIcon(QtGui.QIcon(str(File.from_resource(package=res, name="python_icon", extension="ico"))))
        self.widget.setContextMenu(self.menu)
        self.widget.setToolTip(self.name)

    def add_tray_option(self, name: str, callback: Callable, icon_path: PathLike = None) -> SystemTrayGui:
        action = QtWidgets.QAction(QtGui.QIcon(str(File.from_pathlike(icon_path))), name, self.menu) if icon_path is not None else QtWidgets.QAction(name, self.menu)
        action.triggered.connect(callback)
        self.menu.addAction(action)

        return self

    def notify(self, message: str, level: SystemTrayGui.NotificationLevel = NotificationLevel.INFO, duration: int = 2) -> None:
        self.widget.showMessage(self.name, message, self.notification_mappings.get(level, 1), duration*1000)

    def start(self) -> SystemTrayGui:
        self._add_default_options()
        self.widget.show()
        if self.hide_option is not None:
            self.show()

        self.notify(f"Now running in the background.")

        self.app = QtWidgets.QApplication([])
        self.app.exec()

        return self

    def _add_default_options(self) -> None:
        if self.hide_option:
            self.add_tray_option(name="show/hide", callback=self._trigger, icon_path=File.from_resource(package=res, name="hide_icon", extension="png"))

        self.add_tray_option(name="quit", callback=self._shutdown, icon_path=File.from_resource(package=res, name="quit_icon", extension="png"))

    def _trigger(self) -> None:
        self.hide() if self.isVisible() else self.show()

    def _shutdown(self) -> None:
        self.widget.hide()
        self.end()


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

    def __iter__(self) -> ProgressBarGui:
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
