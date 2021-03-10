from __future__ import annotations

from typing import Any, Callable
import getpass
from traceback import format_exc

from maybe import Maybe
from subtypes import DateTime
from pathmagic import File, Dir, PathLike
from miscutils import executed_within_user_tree

from logbook import (
    FileHandler, LogRecord, Logger,
    CRITICAL, ERROR, WARNING, NOTICE, INFO, DEBUG, TRACE, NOTSET,
    critical, error, warning, notice, info, debug, trace
)

import iotools


class Log(FileHandler):
    """
    A log class intended to provide an alternative FileHandler implementation to the logbook library with additional functionality.
    The first time it is opened it will log the current time and user.
    """

    class LogLevel:
        CRITICAL, ERROR, WARNING, NOTICE, INFO, DEBUG, TRACE, NOT_SET = CRITICAL, ERROR, WARNING, NOTICE, INFO, DEBUG, TRACE, NOTSET

    default_logger: Logger = critical.__self__
    default_logger.name = "main"

    critical, error, warning, notice, info, debug, trace = critical, error, warning, notice, info, debug, trace

    def __init__(self, filename: PathLike, mode="a", encoding: str = None, level: int = LogLevel.NOT_SET,
                 format_string: str = None, delay: bool = True, filter: Callable = None, bubble: bool = False) -> None:
        super().__init__(filename=filename, mode=mode, encoding=encoding, level=level,
                         format_string=format_string, delay=delay, filter=filter, bubble=bubble)

        self.user = getpass.getuser()
        self.file = File.from_pathlike(filename)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __enter__(self) -> Log:
        super().__enter__()
        self.greeting()
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        if ex_type is not None:
            self.handle_exception(ex_value)

        self.goodbye()
        super().__exit__(ex_type, ex_value, ex_traceback)
        self.post_process()

    @property
    def format_string(self) -> None:
        return None

    @format_string.setter
    def format_string(self, value: str) -> None:
        if value is not None:
            if value != self.default_format_string:
                raise ValueError(f"Cannot set 'format_string' directly. Please subclass and override one or several of the following methods:"
                                 f"{type(self).__name__}.{self.format_prefix.__name__}"
                                 f"{type(self).__name__}.{self.format_message.__name__}"
                                 f"{type(self).__name__}.{self.format_message_line.__name__}")

    @property
    def formatter(self) -> Callable:
        return self.format

    @formatter.setter
    def formatter(self, value: Callable) -> None:
        if value is not None:
            raise ValueError(f"Cannot set 'formatter' directly. Please subclass and override one or several of the following methods:\n"
                             f"\n{type(self).__name__}.{self.format_prefix.__name__}"
                             f"\n{type(self).__name__}.{self.format_message.__name__}"
                             f"\n{type(self).__name__}.{self.format_message_line.__name__}")

    def start(self) -> None:
        """Start this log's file using the default application for this type of file."""
        self.file.start()

    def format(self, record: LogRecord):
        if record.level == 100:
            return record.message

        prefix = self.format_prefix(record=record)
        lines = self.format_message(record=record).split("\n")
        return "\n".join(f"{prefix}{self.format_message_line(record=record, line=line)}" for line in lines)

    def format_prefix(self, record: LogRecord) -> str:
        return f"{DateTime.from_datetime(record.time).to_isoformat(timespec='milliseconds')} | {record.channel}.{record.level_name.ljust(8)} | "

    def format_message(self, record: LogRecord) -> str:
        return record.message.strip()

    def format_message_line(self, record: LogRecord, line: str) -> str:
        return line

    def greeting(self):
        self.debug(f"Process executed by user {self.user}")
        self.delimiter_single()

    def goodbye(self):
        return self.delimiter_double()

    def post_process(self) -> None:
        pass

    def handle_exception(self, exception: Exception) -> None:
        self.delimiter_single()
        self.critical(format_exc())

    @classmethod
    def bare(cls, text: str) -> None:
        cls.default_logger.log(100, text)

    @classmethod
    def delimiter_single(cls) -> None:
        """Write a delimiter of hyphens to this log."""
        cls.debug("-"*200)

    @classmethod
    def delimiter_double(cls) -> None:
        """Write a delimiter of equal signs to this log."""
        cls.debug("="*200)

    @classmethod
    def from_details(cls, stem: str, extension: str = "log", dir: PathLike = None, datestamp: bool = True,
                     mode="a", encoding: str = None, level: int = LogLevel.NOT_SET,
                     format_string: str = None, delay: bool = True, filter: Callable = None, bubble: bool = False) -> Log:
        """Create a new Log from the given arguments."""
        default_log_dir = Dir.from_appdata(systemwide=not executed_within_user_tree()).new_dir("python").new_dir("logs").new_dir(iotools.__name__).new_dir("misc")
        logdir = Dir.from_pathlike(Maybe(dir).else_(default_log_dir))
        file = logdir.new_file(f"{DateTime.today().to_filetag()}_{stem}" if datestamp else stem, extension)

        return cls(filename=file, mode=mode, encoding=encoding, level=level, format_string=format_string, delay=delay, filter=filter, bubble=bubble)
