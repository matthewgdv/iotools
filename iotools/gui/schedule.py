from typing import Callable, Any

from apscheduler.schedulers.qt import QtScheduler

from iotools.misc import Schedule
from .gui import SystemTrayGui


class SysTraySchedule(Schedule):
    scheduler_constructor = QtScheduler

    def __init__(self, name: str = "default", on_success: Callable = None, on_failure: Callable = None) -> None:
        super().__init__(name=name, on_success=on_success, on_failure=on_failure)
        self.gui = SystemTrayGui(name=name)

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        super().__exit__(ex_type=ex_type, ex_value=ex_value, ex_traceback=ex_traceback)
        self.gui.start()
