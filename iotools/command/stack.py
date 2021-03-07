from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .declarative import Command, Group


class Stack:
    commands: list[Command] = []
    groups: list[Group] = []
