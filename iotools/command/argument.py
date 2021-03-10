from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Union, Optional, Type, TYPE_CHECKING
import datetime as dt

from pathmagic import File, Dir
from subtypes import Str, List, Dict, Date, DateTime, Enum
from miscutils import ReprMixin, ParametrizableMixin

from iotools.misc import Validator, Validate
from iotools.misc.validator import ListValidator, DictionaryValidator

from .stack import Stack

if TYPE_CHECKING:
    from iotools.gui.widget.base import WidgetHandler


class Argument(ReprMixin):
    """Class representing an argument (and its associated metadata) for the Command and Group classes to use."""
    _registry: dict[Type, Type[Argument]] = {}

    validator_constructor: Type[Validator] = None
    type_affinity: Type = None

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

    def __init_subclass__(cls, **kwargs) -> None:
        if cls.type_affinity is not None:
            cls._registry[cls.type_affinity] = cls

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

    def _post_init_hook(self) -> None:
        pass

    @classmethod
    def infer_subclass(cls, mystery: Type) -> Type[Argument]:
        if (arg_class := cls._registry.get(mystery)) is not None:
            return arg_class

        for type_, arg_type in cls._registry.items():
            if isinstance(mystery, type_):
                return arg_type
        else:
            raise TypeError(f"Don't know how to map an {Argument.__name__} from {mystery.__name__}")


class ParametrizableArgument(Argument, ParametrizableMixin):
    pass


class ParametrizableSizedArgument(ParametrizableArgument):
    widget_magnitude: int = None

    def parametrize(self, param: int) -> ParametrizableSizedArgument:
        if not isinstance(param, int):
            raise TypeError(f"Cannot parametrize {type(self).__name__} with argument of type {type(param).__name__}, must be {int.__name__}")

        self.widget_magnitude = param

        return self


class ParametrizableCollectionArgument(ParametrizableArgument):
    deep_type: Argument = None

    validator: ListValidator

    def parametrize(self, param: Union[Argument, Type]) -> ParametrizableCollectionArgument:
        self.deep_type = param if isinstance(param, Argument) else Argument.infer_subclass(param)()
        self.validator.of_type(deep_type=self.deep_type.validator)

        return self


class ParametrizableMappingArgument(ParametrizableArgument):
    key_type: Argument = None
    val_type: Argument = None

    validator: DictionaryValidator

    def parametrize(self, param: tuple[Union[Argument, Type], Union[Argument, Type]]) -> ParametrizableMappingArgument:
        key, val = param
        self.key_type = param if isinstance(param, Argument) else Argument.infer_subclass(key)()
        self.val_type = param if isinstance(param, Argument) else Argument.infer_subclass(val)()
        self.validator.of_type(key_type=self.key_type.validator, val_type=self.val_type.validator)

        return self


class StringArgument(ParametrizableSizedArgument):
    validator_constructor = Validate.String
    type_affinity = str

    widget_magnitude = 1

    def __call__(self) -> Str:
        return self.value


class BooleanArgument(Argument):
    validator_constructor = Validate.Boolean
    type_affinity = bool

    def __call__(self) -> bool:
        return self.value


class IntegerArgument(Argument):
    validator_constructor = Validate.Integer
    type_affinity = int

    def __call__(self) -> int:
        return self.value


class FloatArgument(Argument):
    validator_constructor = Validate.Float
    type_affinity = float

    def __call__(self) -> float:
        return self.value


class DecimalArgument(Argument):
    validator_constructor = Validate.Decimal
    type_affinity = Decimal

    def __call__(self) -> Decimal:
        return self.value


class DateArgument(Argument):
    validator_constructor = Validate.Date
    type_affinity = dt.date

    def __call__(self) -> Date:
        return self.value


class DateTimeArgument(ParametrizableSizedArgument):
    validator_constructor = Validate.DateTime
    type_affinity = dt.datetime

    widget_magnitude = 6

    def __call__(self) -> DateTime:
        return self.value


class ListArgument(ParametrizableCollectionArgument):
    validator_constructor = Validate.List
    type_affinity = list

    def __call__(self) -> List:
        return self.value


class DictionaryArgument(ParametrizableMappingArgument):
    validator_constructor = Validate.Dict
    type_affinity = dict

    def __call__(self) -> Dict:
        return self.value


class SetArgument(ParametrizableCollectionArgument):
    validator_constructor = Validate.Set
    type_affinity = set

    def __call__(self) -> set:
        return self.value


class PathArgument(Argument):
    validator_constructor = Validate.Path
    type_affinity = Path

    def __call__(self) -> Path:
        return self.value


class FileArgument(Argument):
    validator_constructor = Validate.File
    type_affinity = File

    def __call__(self) -> File:
        return self.value


class DirArgument(Argument):
    validator_constructor = Validate.Dir
    type_affinity = Dir

    def __call__(self) -> Dir:
        return self.value


class ArgType:
    """A namespace for the various validators corresponding to argument types an CommandHandler understands."""
    String, Boolean, Integer, Float, Decimal = StringArgument, BooleanArgument, IntegerArgument, FloatArgument, DecimalArgument
    DateTime, Date = DateTimeArgument, DateArgument
    List, Dict, Set = ListArgument, DictionaryArgument, SetArgument
    Path, File, Dir = PathArgument, FileArgument, DirArgument
