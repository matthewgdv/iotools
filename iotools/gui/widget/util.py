from __future__ import annotations

from typing import Any, Callable


class TemporarilyDisconnect:
    """Utility class used as a context manager to disconnect a callback from a signal and then reconnect it once it drops out of scope."""

    def __init__(self, callback: Callable) -> None:
        self.callback = callback
        self.signal: Any = None

    def from_(self, signal: Any) -> TemporarilyDisconnect:
        """The signal to disconnect the callback from."""
        self.signal = signal
        return self

    def __enter__(self) -> TemporarilyDisconnect:
        self.signal.disconnect(self.callback)
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        self.signal.connect(self.callback)
