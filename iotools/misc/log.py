from __future__ import annotations

from typing import Any, Optional
import getpass

from maybe import Maybe
from subtypes import DateTime, Str
from pathmagic import File, Dir, PathLike
from miscutils import StreamReplacerMixin

from .console import Console


class Log:
    """
    A log class intended to provide a cookie-cutter alternative to the logging module, which allows for much less custimization, but also requires less setup.
    This log has a concept of being active/inactive. A deactivated log will do nothing when written to. The first time it is activated it will log the current time and user.
    When used as a context manager, the log will activate upon entering, and deactivate upon exiting.
    """

    def __init__(self, path: PathLike) -> None:
        self._path, self.user = path, getpass.getuser()
        self._active = self._initialized = False
        self.file: Optional[File] = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __enter__(self) -> Log:
        self.activate()
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        self.deactivate()
        self.post_process()

    @property
    def active(self) -> bool:
        """Set whether this log is active/inactive. A deactivated log will do nothing when written to."""
        return self._active

    @active.setter
    def active(self, val: bool) -> None:
        (self.activate if val else self.deactivate)()

    def activate(self) -> None:
        """Activate this log."""
        if self._path is not None:
            if not self._initialized:
                self._initialize()

            self._active = True

    def deactivate(self) -> None:
        """Deactivate this log. A deactivated log will do nothing when written to."""
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

    def post_process(self) -> None:
        pass

    def _initialize(self) -> None:
        self.file = File(self._path)

        if self.file.content:
            self.file.append(f"{'-' * 200}\n")
        self.file.append(f"-- Process run by user: {self.user} at: {DateTime.now()}\n\n")

        self._initialized = True

    @classmethod
    def from_details(cls, log_name: str, file_extension: str = "txt", log_dir: PathLike = None, active: bool = True) -> Log:
        """Create a new Log from the given arguments."""
        default_log_dir = Dir.from_home().d.documents.new_dir("Python").new_dir("logs")
        logdir = Dir.from_pathlike(Maybe(log_dir).else_(default_log_dir))
        file = logdir.new_file(f"{DateTime.today().to_filetag()}_{log_name}", file_extension)

        return cls(file)


class PrintLog(Log, StreamReplacerMixin):
    """A subclass of miscutils.Log directed at capturing the sys.stdout stream and logging it, in addition to still writing to sys.stdout (though this can be controlled with arguments)."""

    def __init__(self, path: PathLike, active: bool = True, to_stream: bool = True, to_file: bool = True) -> None:
        super().__init__(path=path)
        self.to_stream, self.to_file = to_stream, to_file

    def __call__(self, to_stream: bool = True, to_file: bool = True) -> PrintLog:
        self.to_stream, self.to_file = to_stream, to_file
        return self

    def __enter__(self) -> PrintLog:
        super().__enter__()
        StreamReplacerMixin.__enter__(self)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        super().__exit__(ex_type=ex_type, ex_value=ex_value, ex_traceback=ex_traceback)
        StreamReplacerMixin.__exit__(self, ex_type=ex_type, ex_value=ex_value, ex_traceback=ex_traceback)

    def write(self, text: str, to_stream: bool = None, to_file: bool = None, add_newlines: int = 0) -> None:
        """Write the given text to this log's file and to sys.stdout, based on the 'to_console' and 'to_file' attributes set by the constructor. These attributes can be overriden by the arguments in this call."""
        if Maybe(to_stream).else_(self.to_stream):
            self.stream.write(text + "\n"*add_newlines)

        if Maybe(to_file).else_(self.to_file):
            super().write(text, add_newlines=add_newlines)

    def post_process(self) -> None:
        if (clear_line := f"{Console.UP_ONE_LINE}{Console.CLEAR_CURRENT_LINE}") in (text := self.file.content):
            lines, escaped_clear_line, out_lines, skip_counter = reversed(text.split("\n")), Str(clear_line).re.escape(), [], 0
            for index, line in enumerate(lines):
                num_to_clear = line.count(clear_line)
                if skip_counter:
                    skip_counter -= 1
                else:
                    out_lines.append(Str(line).slice.after_last(escaped_clear_line) if num_to_clear else line)

                if num_to_clear:
                    skip_counter = max([skip_counter, num_to_clear])

            self.file.content = "\n".join(reversed(out_lines))
