from typing import Callable, Any, Optional

from apscheduler.schedulers.base import BaseScheduler
from PySide6.QtCore import QTimer

from iotools.misc import Schedule
from .gui import SystemTrayGui


class QtScheduler(BaseScheduler):
    """A scheduler that runs in a Qt event loop."""

    _timer: Optional[QTimer] = None

    def wakeup(self):
        self._start_timer(0)

    def shutdown(self, *args, **kwargs):
        super().shutdown(*args, **kwargs)
        self._stop_timer()

    def _start_timer(self, wait_seconds):
        self._stop_timer()
        if wait_seconds is not None:
            wait_time = min(wait_seconds*1000, 2147483647)
            self._timer = QTimer.singleShot(wait_time, self._process_jobs)

    def _stop_timer(self):
        if self._timer:
            if self._timer.isActive():
                self._timer.stop()
            del self._timer

    def _process_jobs(self):
        wait_seconds = super()._process_jobs()
        self._start_timer(wait_seconds)


class SystemTraySchedule(Schedule):
    """
    A class used to specify schedules on which specific Python callables will be executed. Event callbacks can be supplied to be invoked on success
    or failure.

    Normal usage is to use this class as a context manager, instanciating it in 'with' clause, and specifying the schedules within the
    'with' block.

    Upon exiting the application will block, a system tray icon will be created, and the schedules will execute until a user exits
    out of the GUI using the provided system tray menu option.
    """

    scheduler_constructor = QtScheduler

    def __init__(self, name: str = "default", on_success: Callable = None, on_failure: Callable = None) -> None:
        super().__init__(name=name, on_success=on_success, on_failure=on_failure)
        self.gui = SystemTrayGui(name=name)

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        super().__exit__(ex_type=ex_type, ex_value=ex_value, ex_traceback=ex_traceback)
        self.gui.start()
