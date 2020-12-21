from typing import Callable, Any

from apscheduler.schedulers.qt import QtScheduler

from iotools.misc import Schedule
from .gui import SystemTrayGui


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
