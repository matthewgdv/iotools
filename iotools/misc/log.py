from __future__ import annotations

from typing import Any, Optional
import sys
import os
import getpass

from maybe import Maybe
from subtypes import DateTime
from pathmagic import File, Dir, PathLike


class Log:
    """
    A log class intended to provide a cookie-cutter alternative to the logging module, which allows for much less custimization, but also requires less setup.
    This log has a concept of being active/inactive. A deactivated log will do nothing when written to. The first time it is activated it will log the current time and user.
    When used as a context manager, the log will activate upon entering, and deactivate upon exiting.
    """

    def __init__(self, path: PathLike, active: bool = True) -> None:
        self._path, self.user = path, getpass.getuser()
        self._active = self._initialized = False
        self.file: Optional[File] = None

        if active:
            self.activate()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __enter__(self) -> Log:
        self.activate()
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        self.deactivate()

    @property
    def active(self) -> bool:
        """Set whether this log is active/inactive. A deactivated log will do nothing when written to."""
        return self._active

    @active.setter
    def active(self, val: bool) -> None:
        (self.activate if val else self.deactivate)()

    def activate(self) -> None:
        """Activate this log."""
        if not self._initialized:
            self._initialize()

        if not self._active:
            self._active = True

    def deactivate(self) -> None:
        """Deactivate this log. A deactivated log will do nothing when written to."""
        if self._active:
            self._active = False

    def write(self, text: str, add_newlines: int = 2) -> None:
        """Write the given text this log, optionally appending newlines."""
        if self.active:
            br = "\n"
            self.file.content += f"{text}{br*add_newlines}"

    def write_delimiter(self, length: int = 200, add_newlines: int = 2) -> None:
        """Write a delimiter of hyphens to this log, optionally appending newlines."""
        if self.active:
            br = "\n"
            self.file.content += f"{'-'*length}{br*add_newlines}"

    def start(self) -> None:
        """Start this log's file using the default application for this type of file."""
        self.file.start()

    def _initialize(self) -> None:
        self.file = File(self._path)
        self.file.append(f"{'-' * 200}\n" if self.file.content else "")
        self.file.append(f"-- Process run by user: {self.user} at: {DateTime.now()}\n\n")
        self._initialized = True

    @classmethod
    def from_details(cls, log_name: str, file_extension: str = "txt", log_dir: PathLike = None, active: bool = True) -> Log:
        """Create a new Log from the given arguments."""
        default_log_dir = Dir.from_home().d.documents.new_dir("Python").new_dir("logs")
        logdir = Dir.from_pathlike(Maybe(log_dir).else_(default_log_dir))
        path = fR"{logdir}{os.sep}{log_name}Log{DateTime.now().to_filetag()}{file_extension if file_extension.startswith('.') else f'.{file_extension}'}"

        return cls(path, active=active)


class PrintLog(Log):
    """A subclass of miscutils.Log directed at capturing the sys.stdout stream and logging it, in addition to still writing to sys.stdout (though this can be controlled with arguments)."""
    initial = sys.stdout
    stack: Any = []

    def __init__(self, path: PathLike, active: bool = True, to_console: bool = True, to_file: bool = True) -> None:
        super().__init__(path=path, active=active)
        self.to_console, self.to_file = to_console, to_file

    def __call__(self, to_console: bool = True, to_file: bool = True) -> PrintLog:
        self.to_console, self.to_file = to_console, to_file
        return self

    def __enter__(self) -> PrintLog:
        self.stack.append(sys.stdout)
        sys.stdout = self
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        sys.stdout = self.stack.pop(-1)

    def write(self, text: str, to_console: bool = None, to_file: bool = None, add_newlines: int = 0) -> None:
        """Write the given text to this log's file and to sys.stdout, based on the 'to_console' and 'to_file' attributes set by the constructor. These attributes can be overriden by the arguments in this call."""
        if Maybe(to_console).else_(self.to_console):
            self.initial.write(text + "\n"*add_newlines)

        if Maybe(to_file).else_(self.to_file):
            try:
                super().write(text, add_newlines=add_newlines)
            except UnicodeEncodeError:
                pass

    def flush(self) -> None:
        """Flush the sys.stdout stream."""
        self.initial.flush()
