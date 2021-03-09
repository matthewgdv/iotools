from __future__ import annotations

from .nested import IndentationLog, StackFrameLog
from .print_log import PrintLog


class IndentationPrintLog(PrintLog, IndentationLog):
    pass


class StackFramePrintLog(PrintLog, StackFrameLog):
    pass
