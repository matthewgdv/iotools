from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterator, Union, Optional, Type, TYPE_CHECKING

from pathmagic import File, Dir
from subtypes import Date, DateTime, Enum
from miscutils import ReprMixin, cached_property

from iotools.misc import Validator, Validate
from iotools.misc.validator import CollectionValidator

if TYPE_CHECKING:
    from iotools.gui.widget import WidgetHandler


class Argument(ReprMixin):
    """Class representing an argument (and its associated metadata) for the ArgHandler and ArgsGui to use."""

    validator_constructor: Type[Validator] = None

    def __init__(self, name: str = None, aliases: list[str] = None, info: str = None, default: Any = None, nullable: bool = False, required: bool = None,
                 conditions: Union[Callable, list[Callable], dict[str, Callable]] = None, choices: Union[Type[Enum], list] = None) -> None:
        self._value = None

        self.name, self.aliases, self.info, self.default, self.nullable, self.required = name, aliases, info, default, nullable, required
        self.required = required if required is not None else (True if self.default is None and not self.nullable else False)

        self.choices: list = [member.value for member in choices] if Enum.is_enum(choices) else choices
        self.validator = self.validator_constructor(nullable=bool(self.nullable), choices=self.choices)

        if conditions:
            self.validator.add_conditions(conditions) if isinstance(list, dict) else self.validator.add_condition(conditions)

        self.widget: Optional[WidgetHandler] = None

        self._try_to_add_self_to_top_of_stack()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __str__(self) -> str:
        raise TypeError(f"Cannot implicitly stringify a {type(self).__name__}.")

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
        return [self.name] if self._aliases is None else sorted({self.name, *self._aliases}, key=len)

    @aliases.setter
    def aliases(self, val: list[str]) -> None:
        self._aliases = val

    @property
    def default(self) -> Any:
        return self._default

    @default.setter
    def default(self, val: Any) -> None:
        self._default = val

        if self._value is None:
            self._value = val

    @cached_property
    def commandline_aliases(self) -> list[str]:
        return [f"--{name}" if len(name) > 1 else f"-{name}" for name in self.aliases]

    def _try_to_add_self_to_top_of_stack(self):
        from .command import CommandMeta

        if CommandMeta.stack:
            CommandMeta.stack[-1]._handler_.add_argument(self)


class SizedWidgetArgument(Argument):
    def __init__(self, name: str = None, aliases: list[str] = None, info: str = None, default: Any = None, nullable: bool = False, required: bool = None,
                 conditions: Union[Callable, list[Callable], dict[str, Callable]] = None, choices: Union[Type[Enum], list] = None, widget_magnitude: int = None) -> None:
        super().__init__(name, aliases, info, default, nullable, required, conditions, choices)
        self.widget_magnitude = widget_magnitude


class DeepTypedArgument(Argument):
    validator: CollectionValidator

    def __init__(self, name: str = None, aliases: list[str] = None, info: str = None, default: Any = None, nullable: bool = False, required: bool = None,
                 conditions: Union[Callable, list[Callable], dict[str, Callable]] = None, choices: Union[Type[Enum], list] = None, deep_type: Any = None) -> None:
        super().__init__(name, aliases, info, default, nullable, required, conditions, choices)
        self.validator.of_type(deep_type)


class StringArgument(SizedWidgetArgument):
    validator_constructor = Validate.String

    def __call__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value


class BooleanArgument(Argument):
    validator_constructor = Validate.Boolean

    def __call__(self) -> bool:
        return self.value

    def __bool__(self) -> bool:
        return self.value


class IntegerArgument(Argument):
    validator_constructor = Validate.Integer

    def __call__(self) -> int:
        return self.value

    def __int__(self) -> int:
        return self.value


class FloatArgument(Argument):
    validator_constructor = Validate.Float

    def __call__(self) -> float:
        return self.value

    def __float__(self) -> float:
        return self.value


class DecimalArgument(Argument):
    validator_constructor = Validate.Decimal

    def __call__(self) -> Decimal:
        return self.value


class DateArgument(Argument):
    validator_constructor = Validate.Date

    def __call__(self) -> Date:
        return self.value

    def __str__(self) -> str:
        return str(self.value)


class DateTimeArgument(SizedWidgetArgument):
    validator_constructor = Validate.DateTime

    def __call__(self) -> DateTime:
        return self.value

    def __str__(self) -> str:
        return str(self.value)


class ListArgument(DeepTypedArgument):
    validator_constructor = Validate.List

    validator: Type[Validate.List]

    def __call__(self) -> list:
        return self.value

    def __iter__(self) -> Iterator:
        return iter(self.value)


class DictArgument(DeepTypedArgument):
    validator_constructor = Validate.Dict

    validator: Type[Validate.Dict]

    def __call__(self) -> dict:
        return self.value

    def __iter__(self) -> Iterator:
        return iter(self.value)

    def __getitem__(self, item: Any) -> Any:
        return self.value[item]

    def keys(self) -> Any:
        return self.value.keys()


class SetArgument(DeepTypedArgument):
    validator_constructor = Validate.Set

    validator: Type[Validate.Set]

    def __call__(self) -> set:
        return self.value

    def __iter__(self) -> Iterator:
        return iter(self.value)


class PathArgument(Argument):
    validator_constructor = Validate.Path

    def __call__(self) -> Path:
        return self.value

    def __str__(self) -> str:
        return str(self.value)


class FileArgument(Argument):
    validator_constructor = Validate.File

    def __call__(self) -> File:
        return self.value

    def __str__(self) -> str:
        return str(self.value)


class DirArgument(Argument):
    validator_constructor = Validate.Dir

    def __call__(self) -> Dir:
        return self.value

    def __str__(self) -> str:
        return str(self.value)


class ArgType:
    """A namespace for the various validators corresponding to argument types an ArgHandler understands."""
    String, Boolean, Integer, Float, Decimal = StringArgument, BooleanArgument, IntegerArgument, FloatArgument, DecimalArgument
    DateTime, Date = DateTimeArgument, DateArgument
    List, Dict, Set = ListArgument, DictArgument, SetArgument
    Path, File, Dir = PathArgument, FileArgument, DirArgument


# class Dependency:
#     class Mode(Enum):
#         ALL, ANY = "all", "any"
#
#     def __init__(self, dependency: Union[Argument, list[Argument]], argument: Argument = None, mode: Dependency.Mode = Mode.ANY) -> None:
#         self.dependencies: list[Argument] = [dependency] if isinstance(dependency, Argument) else dependency
#         self.argument, self.mode = argument, self.Mode(mode).map_to({self.Mode.ALL: all, self.Mode.ANY: any})
#
#     def __repr__(self) -> str:
#         return f"{type(self).__name__}(argument={self.argument}, arguments=[{', '.join(arg.name for arg in self.dependencies)}], mode={self.mode.__name__})"
#
#     def __str__(self) -> str:
#         return f"{', '.join(arg.name for arg in self.dependencies)} [{self.mode.__name__}]"
#
#     def __bool__(self) -> bool:
#         return self.mode([bool(argument.value) for argument in self.dependencies])
#
#     def validate(self) -> bool:
#         if self:
#             if self.argument.value is None:
#                 raise ValueError(f"""Must provide a value for argument '{self.argument}' if {self.mode.__name__} of: {", ".join(f"'{arg}'" for arg in self.dependencies)} are truthy.""")
#         else:
#             if self.argument.value is not None:
#                 raise ValueError(f"""May not provide a value for argument '{self.argument}' unless {self.mode.__name__} of: {", ".join(f"'{arg}'" for arg in self.dependencies)} are truthy.""")
#
#         return True
#
#
# class Nullability:
#     def __init__(self, truth: bool, argument: Argument) -> None:
#         self.truth, self.argument = truth, argument
#
#     def __repr__(self) -> str:
#         return f"{type(self).__name__}(truth={self.truth}, bool={bool(self)})"
#
#     def __str__(self) -> str:
#         return str(self.truth)
#
#     def __bool__(self) -> bool:
#         return self.truth if self.argument.dependency is None else True
