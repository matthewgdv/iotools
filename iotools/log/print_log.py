from __future__ import annotations

from typing import Any, Callable

from subtypes import Str
from pathmagic import PathLike
from miscutils import StdOutReplacerMixin

from .base import Log


class StdOutLogRedirector(StdOutReplacerMixin):
    def __init__(self, log: PrintLog) -> None:
        self.log = log

    def write(self, text: str) -> None:
        super().write(text)
        if clean := text.strip():
            self.log.info(clean)


class PrintLog(Log):
    """A subclass of Log directed at capturing the sys.stdout stream and logging it, in addition to still writing to sys.stdout (though this can be controlled with arguments)."""

    def __init__(self, filename: PathLike, mode="a", encoding: str = None, level: int = Log.LogLevel.NOT_SET,
                 format_string: str = None, delay: bool = True, filter: Callable = None, bubble: bool = False) -> None:
        super().__init__(filename=filename, mode=mode, encoding=encoding, level=level,
                         format_string=format_string, delay=delay, filter=filter, bubble=bubble)
        self.redirector = StdOutLogRedirector(log=self)

    def __enter__(self) -> PrintLog:
        super().__enter__()
        self.redirector.__enter__()
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        super().__exit__(ex_type, ex_value, ex_traceback)
        self.redirector.__exit__(ex_type, ex_value, ex_traceback)

    def post_process(self) -> None:
        from iotools import Console

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
