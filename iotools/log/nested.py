from __future__ import annotations

import os
from typing import Callable
import inspect
from contextlib import contextmanager
from types import FrameType

from logbook import LogRecord

from pathmagic import PathLike

from .base import Log


class BaseNestedLog(Log):
    indentation_level: int

    def __init__(self, filename: PathLike, mode="a", encoding: str = None, level: int = Log.LogLevel.NOT_SET,
                 format_string: str = None, delay: bool = True, filter: Callable = None, bubble: bool = False,
                 indentation_token: str = "    ") -> None:
        super().__init__(filename=filename, mode=mode, encoding=encoding, level=level,
                         format_string=format_string, delay=delay, filter=filter, bubble=bubble)
        self.indentation_token = indentation_token
        self.indent = True

    def format_message_line(self, record: LogRecord, line: str) -> str:
        return f"{self.indentation_token*self.indentation_level if self.indent else ''}{super().format_message_line(record=record, line=line)}"

    def greeting(self):
        with self.no_indentation():
            super().greeting()

    def goodbye(self):
        with self.no_indentation():
            super().goodbye()

    def handle_exception(self, exception: Exception) -> None:
        with self.no_indentation():
            super().handle_exception(exception)

    @contextmanager
    def no_indentation(self) -> StackFrameLog:
        indent = self.indent
        self.indent = False
        yield self
        self.indent = indent


class IndentationLog(BaseNestedLog):
    def __init__(self, filename: PathLike, mode="a", encoding: str = None, level: int = Log.LogLevel.NOT_SET,
                 format_string: str = None, delay: bool = True, filter: Callable = None, bubble: bool = False,
                 indentation_token: str = "    ") -> None:
        super().__init__(filename=filename, mode=mode, encoding=encoding, level=level,
                         format_string=format_string, delay=delay, filter=filter, bubble=bubble)
        self.indentation_level = 0

    @contextmanager
    def indentation(self) -> IndentationLog:
        self.indentation_level += 1
        yield self
        self.indentation_level -= 1


class StackFrameLog(BaseNestedLog):
    def __init__(self, filename: PathLike, mode="a", encoding: str = None, level: int = Log.LogLevel.NOT_SET,
                 format_string: str = None, delay: bool = True, filter: Callable = None, bubble: bool = False,
                 indentation_token: str = "    ") -> None:
        super().__init__(filename=filename, mode=mode, encoding=encoding, level=level,
                         format_string=format_string, delay=delay, filter=filter, bubble=bubble,
                         indentation_token=indentation_token)
        self.frames: list[FrameType] = []

    def __enter__(self) -> StackFrameLog:
        self.frames.clear()
        return super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.frames.clear()
        super().__exit__(exc_type, exc_val, exc_tb)

    def format(self, record: LogRecord) -> str:
        if self.indent:
            self.refresh_frames(record=record)
        return super().format(record=record)

    @property
    def indentation_level(self) -> int:
        return len(self.frames) - 1

    def refresh_frames(self, record: LogRecord) -> None:
        record_frames = self.true_frames(record.frame)
        topmost_record_frame = record_frames[0]

        if not self.frames:
            self.frames.append(topmost_record_frame)
            return

        for frame in self.frames[::-1]:
            if frame not in record_frames:
                self.frames.pop()
            else:
                if frame != topmost_record_frame:
                    self.frames.append(topmost_record_frame)

                return

    @classmethod
    def true_frames(cls, frame: FrameType) -> list[FrameType]:
        return [info.frame for info in inspect.getouterframes(frame) if not info.filename.endswith(f"logbook{os.sep}base.py")]
