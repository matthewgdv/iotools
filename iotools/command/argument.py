from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Union, Optional, Type, TYPE_CHECKING

from pathmagic import File, Dir
from subtypes import Date, DateTime, Enum
from miscutils import ReprMixin

from iotools.misc import Validator, Validate
from iotools.misc.validator import CollectionValidator

from .stack import Stack

if TYPE_CHECKING:
    from iotools.gui.widget import WidgetHandler


class Argument(ReprMixin):
    """Class representing an argument (and its associated metadata) for the Command and Group classes to use."""

    validator_constructor: Type[Validator] = None

    def __init__(self, name: str = None, aliases: list[str] = None, info: str = None, default: Any = None, nullable: bool = False,
                 conditions: Union[Callable, list[Callable], dict[str, Callable]] = None, choices: Union[Type[Enum], list] = None) -> None:
        self.name, self.aliases, self.info, self.nullable = name, aliases, info, nullable
        self.default = self._value = default
        self.required = self.default is None and not self.nullable

        self.choices: list = [member.value for member in choices] if Enum.is_enum(choices) else choices
        self.validator = self.validator_constructor(nullable=bool(self.nullable), choices=self.choices)

        if conditions:
            self.validator.add_conditions(conditions) if isinstance(conditions, (list, dict)) else self.validator.add_condition(conditions)

        self.widget: Optional[WidgetHandler] = None

        if Stack.commands:
            Stack.commands[-1]._handler_.add_argument(self)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __bool__(self) -> bool:
        return self.nullable or self.value is not None

    def __call__(self) -> Any:
        return self.value

    @property
    def value(self) -> Any:
        """Property controlling access to the value held by this argument. Setting it will cause validation and coercion to the type of this argument."""
        return self._value

    @value.setter
    def value(self, val: Any) -> None:
        self._value = self.validator.convert(val)

    @property
    def aliases(self) -> list[str]:
        return sorted([f"--{name}" if len(name) > 1 else f"-{name}" for name in self._aliases if name], key=len)

    @aliases.setter
    def aliases(self, val: list[str]) -> None:
        self._aliases = {self.name, *(val or [])}


class SizedWidgetArgument(Argument):
    def __init__(self, name: str = None, aliases: list[str] = None, info: str = None, default: Any = None, nullable: bool = False,
                 conditions: Union[Callable, list[Callable], dict[str, Callable]] = None, choices: Union[Type[Enum], list] = None, widget_magnitude: int = None) -> None:
        super().__init__(name=name, aliases=aliases, info=info, default=default, nullable=nullable, conditions=conditions, choices=choices)
        self.widget_magnitude = widget_magnitude


class DeepTypedArgument(Argument):
    validator: CollectionValidator

    def __init__(self, name: str = None, aliases: list[str] = None, info: str = None, default: Any = None, nullable: bool = False,
                 conditions: Union[Callable, list[Callable], dict[str, Callable]] = None, choices: Union[Type[Enum], list] = None, deep_type: Any = None) -> None:
        super().__init__(name=name, aliases=aliases, info=info, default=default, nullable=nullable, conditions=conditions, choices=choices)
        self.validator.of_type(deep_type)


class StringArgument(SizedWidgetArgument):
    validator_constructor = Validate.String

    def __call__(self) -> str:
        return self.value


class BooleanArgument(Argument):
    validator_constructor = Validate.Boolean

    def __call__(self) -> bool:
        return self.value


class IntegerArgument(Argument):
    validator_constructor = Validate.Integer

    def __call__(self) -> int:
        return self.value


class FloatArgument(Argument):
    validator_constructor = Validate.Float

    def __call__(self) -> float:
        return self.value


class DecimalArgument(Argument):
    validator_constructor = Validate.Decimal

    def __call__(self) -> Decimal:
        return self.value


class DateArgument(Argument):
    validator_constructor = Validate.Date

    def __call__(self) -> Date:
        return self.value


class DateTimeArgument(SizedWidgetArgument):
    validator_constructor = Validate.DateTime

    def __call__(self) -> DateTime:
        return self.value


class ListArgument(DeepTypedArgument):
    validator_constructor = Validate.List

    def __call__(self) -> list:
        return self.value


class DictArgument(DeepTypedArgument):
    validator_constructor = Validate.Dict

    def __call__(self) -> dict:
        return self.value


class SetArgument(DeepTypedArgument):
    validator_constructor = Validate.Set

    def __call__(self) -> set:
        return self.value


class PathArgument(Argument):
    validator_constructor = Validate.Path

    def __call__(self) -> Path:
        return self.value


class FileArgument(Argument):
    validator_constructor = Validate.File

    def __call__(self) -> File:
        return self.value


class DirArgument(Argument):
    validator_constructor = Validate.Dir

    def __call__(self) -> Dir:
        return self.value


class ArgType:
    """A namespace for the various validators corresponding to argument types an CommandHandler understands."""
    String, Boolean, Integer, Float, Decimal = StringArgument, BooleanArgument, IntegerArgument, FloatArgument, DecimalArgument
    DateTime, Date = DateTimeArgument, DateArgument
    List, Dict, Set = ListArgument, DictArgument, SetArgument
    Path, File, Dir = PathArgument, FileArgument, DirArgument
