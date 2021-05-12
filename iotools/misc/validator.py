from __future__ import annotations

import datetime as dt
from typing import Any, Generic, TypeVar, Union, Callable, Iterable, Optional, Type
import pathlib
import enum
import decimal

import typepy

from maybe import Maybe
from subtypes import DateTime, Date, Str, List, Dict
import pathmagic
from miscutils import ParametrizableMixin, issubclass_safe, lambda_source


E = TypeVar("E", bound=enum.Enum)


class TypeConversionError(typepy.TypeConversionError):
    """An exception class representing failed conversion of one type to another."""

    def __init__(self, validator: Validator, value: Any) -> None:
        super().__init__(f"Failed {'' if validator.nullable else 'non-'}nullable conversion of {repr(value)} (type {type(value).__name__}) to type {validator.converter.__name__}.")


class Condition:
    """A class representing a condition which must be met in order for a value to pass validation."""

    def __init__(self, condition: Callable[..., bool], name: str = None) -> None:
        self.condition = condition
        self.name = name if name is not None else self.extract_name_from_condition()

    def __str__(self) -> str:
        return Maybe(self.name).else_(self.condition.__name__)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={repr(self.name)}, condition={self.condition.__name__})"

    def __call__(self, input_val: Any) -> bool:
        return self.condition(input_val)

    def extract_name_from_condition(self) -> str:
        return Str(lambda_source(self.condition)).slice.after_first(r":").strip() if self.condition.__name__ == "<lambda>" else self.condition.__name__


class ValidatorMeta(type):
    registry = {}

    def __init__(cls: Type[Validator], name: str, bases: tuple, namespace: dict) -> None:
        if cls.type_affinity is not None:
            cls.registry[cls.type_affinity] = cls


class Validator(metaclass=ValidatorMeta):
    """Abstract validator class providing the interface for concrete validators. The most important methods are Validator.is_valid() and Validator.convert()."""
    type_affinity = None
    converter = None

    def __init__(self, *, nullable: bool = False) -> None:
        self.nullable = nullable
        self.choices: Optional[set] = None
        self.conditions: list[Condition] = []
        self.converter_kwargs: dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"""{type(self).__name__}({", ".join([f"{attr}={repr(val) if not 'type_affinity' in attr else (None if val is None else val.__name__)}" for attr, val in self.__dict__.items() if not attr.startswith('_')])})"""

    def __str__(self) -> str:
        return self.converter.__name__

    def __call__(self, value: Any) -> Any:
        return self.convert(value)

    def set_nullable(self, nullable: bool = True) -> Validator:
        self.nullable = nullable
        return self

    def set_choices(self, choices: Union[enum.Enum, Iterable] = None) -> Validator:
        self.choices = None if choices is None else (
            [member.value for member in choices] if issubclass_safe(choices, enum.Enum) else list(choices)
        )
        return self

    def add_condition(self, condition: Callable, name: str = None) -> Validator:
        self.conditions.append(Condition(condition=condition, name=name))
        return self

    def add_conditions(self, conditions: Union[list[Callable], dict[str, Callable]]) -> Validator:
        self.conditions += [Condition(condition=cond, name=name) for name, cond in conditions.items()] if isinstance(conditions, dict) else [Condition(condition=cond) for cond in conditions]
        return self

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return bool(self.nullable)

        value = self._pre_process(value)

        if not self.converter(value, strict_level=typepy.StrictLevel.MIN, **self.converter_kwargs).is_type():
            return False

        try:
            self.convert(value)
            return True
        except (ValueError, TypeConversionError):
            return False

    def convert(self, value: Any) -> Any:
        if value is None:
            if self.nullable:
                return None
            else:
                raise TypeConversionError(self, value)

        value = self._pre_process(value)

        try:
            ret = self.converter(value, strict_level=typepy.StrictLevel.MIN, **self.converter_kwargs).convert()
        except typepy.TypeConversionError:
            raise TypeConversionError(self, value)

        if self.choices is not None and ret not in self.choices:
            raise ValueError(f"Value '{value}' is not a valid choice. Valid choices are: {', '.join([repr(option) for option in self.choices])}.")

        for condition in self.conditions:
            if not condition(ret):
                raise ValueError(f"Value '{value}' does not satisfy the condition: '{condition}'.")

        return self._to_subtype(ret)

    def _to_subtype(self, value: Any) -> Any:
        return value

    def _pre_process(self, value: Any) -> Any:
        return value


class AnythingValidator(Validator):
    """A validator that will always return True on Validator.is_valid() and will return the original value on Validator.convert()."""
    class Anything:
        def __init__(self, value: Any, *args: Any, **kwargs: Any) -> None:
            self.value = value

        def is_type(self) -> bool:
            return True

        def convert(self) -> Any:
            return self.value

    converter = Anything


class UnknownTypeValidator(Validator):
    """A validator that will always return True on Validator.is_valid() and will use the constructor provided to it as a callback for Validator.convert()."""
    converter = AnythingValidator.Anything

    def __init__(self, constructor: Any, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._constructor = constructor

    def convert(self, value) -> Any:
        return self._constructor(super().convert(value))


class BooleanValidator(Validator):
    """A validator that can handle booleans."""
    type_affinity, converter = bool, typepy.Bool
    converter.__name__ = "Boolean"


class StringValidator(Validator):
    """A validator that can handle strings."""
    type_affinity, converter = str, typepy.String

    def max_len(self, length: int) -> StringValidator:
        self.conditions.append(Condition(lambda val: len(val) <= length, name=f"len(val) <= {length}"))
        return self

    def min_len(self, length: int) -> StringValidator:
        self.conditions.append(Condition(lambda val: len(val) >= length, name=f"len(val) >= {length}"))
        return self

    def _to_subtype(self, value: str) -> Str:
        return Str(value)


class NumericValidator(Validator):
    def max_value(self, value: int) -> NumericValidator:
        self.conditions.append(Condition(lambda val: val <= value, name=f"val <= {value}"))
        return self

    def min_value(self, value: int) -> NumericValidator:
        self.conditions.append(Condition(lambda val: val >= value, name=f"val >= {value}"))
        return self


class IntegerValidator(NumericValidator):
    """A validator that can handle integers."""
    type_affinity, converter = int, typepy.Integer


class FloatValidator(NumericValidator):
    """A validator that can handle floating points numbers."""
    class Float(typepy.RealNumber):
        def convert(self) -> float:
            return float(super().convert())

    type_affinity, converter = float, Float


class DecimalValidator(NumericValidator):
    """A validator that can handle decimal numbers."""
    class Decimal(typepy.RealNumber):
        pass

    type_affinity, converter = decimal.Decimal, Decimal


class ParametrizableValidator(Validator, ParametrizableMixin):
    def _pre_process(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = eval(value, {}, {})
            except Exception:
                pass

        return value


class ListValidator(ParametrizableValidator):
    """A validator that can handle lists. Item access can be used to create a new validator class that will also validate the type of the list members."""
    type_affinity, converter = list, typepy.List

    def __init__(self, *, nullable: bool = False) -> None:
        super().__init__(nullable=nullable)
        self.deep_type: Optional[Validator] = None

    def __str__(self) -> str:
        return f"""{super().__str__()}{f"[{self.deep_type.converter.__name__}]" if self.deep_type is not None else ""}"""

    def parametrize(self, param: Any) -> ListValidator:
        self.of_type(deep_type=param)
        return self

    def of_type(self, deep_type: Any) -> ListValidator:
        self.deep_type = Validate.infer_type(deep_type, nullable=True)
        return self

    def is_valid(self, value: Any) -> bool:
        valid = super().is_valid(value)
        if self.deep_type is None:
            return valid
        else:
            if valid:
                return all([self.deep_type.is_valid(item) for item in super().convert(value)])
            else:
                return False

    def convert(self, value: Any) -> Optional[list]:
        if (converted := super().convert(value)) is None or self.deep_type is None:
            return converted
        else:
            return [self.deep_type(item) for item in converted]

    def _to_subtype(self, value: list) -> List:
        return List(value)


class SetValidator(ListValidator):
    """A validator that can handle floating points numbers."""
    class Set(typepy.List):
        def convert(self) -> set:
            return set(super().convert())

    type_affinity, converter = set, Set


class DictionaryValidator(ParametrizableValidator):
    """A validator that can handle dicts. Item access can be used to create a new validator class that will also validate the type of the dict's keys and values."""
    type_affinity, converter = dict, typepy.Dictionary

    def __init__(self, *, nullable: bool = False) -> None:
        super().__init__(nullable=nullable)
        self.key_type: Optional[Validator] = None
        self.val_type: Optional[Validator] = None

    def __str__(self) -> str:
        return f"""{super().__str__()}{f"[{self.key_type.converter.__name__}, {self.val_type.converter.__name__}]" if self.is_parametrized else ""}"""

    @property
    def is_parametrized(self):
        return not (self.key_type is None and self.val_type is None)

    def parametrize(self, param: Any) -> DictionaryValidator:
        key, val = param
        self.of_type(key_type=key, val_type=val)
        return self

    def of_type(self, key_type: Any, val_type: Any) -> DictionaryValidator:
        self.key_type = Validate.infer_type(key_type, nullable=True)
        self.val_type = Validate.infer_type(val_type, nullable=True)

        return self

    def is_valid(self, value: Any) -> bool:
        valid = super().is_valid(value)
        if not self.is_parametrized:
            return valid
        else:
            if valid:
                converted = super().convert(value)
                return all([self.key_type.is_valid(item) for item in converted.keys()]) and all([self.val_type.is_valid(item) for item in converted.values()])
            else:
                return False

    def convert(self, value: Any) -> Optional[dict]:
        if (converted := super().convert(value)) is None or not self.is_parametrized:
            return converted
        else:
            return {self.key_type(key): self.val_type(val) for key, val in converted.items()}

    def _to_subtype(self, value: dict) -> Dict:
        return Dict(value)


class DateTimeValidator(Validator):
    """A validator that can handle datetimes. Returns a subtypes.DateTime instance on Validator.convert(). If a datetime.datetime object is desired, call DateTime.to_datetime()."""
    type_affinity, converter = dt.datetime, typepy.DateTime

    def before(self, date: dt.date) -> DateTimeValidator:
        self.conditions.append(Condition(condition=lambda val: val < date, name=f"val < {date}"))
        return self

    def after(self, date: dt.date) -> DateTimeValidator:
        self.conditions.append(Condition(condition=lambda val: val > date, name=f"val > {date}"))
        return self

    def _to_subtype(self, value: dt.datetime) -> DateTime:
        return DateTime.from_datetime(value)


class DateValidator(DateTimeValidator):
    """A validator that can handle dates. Returns a subtypes.Date instance on Validator.convert(). If a datetime.date object is desired, call Date.to_date()."""
    class Date(typepy.DateTime):
        def convert(self) -> dt.date:
            datetime = super().convert()
            return dt.date(datetime.year, datetime.month, datetime.day)

    type_affinity, converter = dt.date, Date

    def _to_subtype(self, value: dt.datetime) -> Date:
        return Date.from_date(value)


class PathValidator(Validator):
    """A validator that can handle filesystem paths. returns a pathlib.Path instance on Validator.convert()."""
    class Path:
        def __init__(self, value: Any, *args: Any, **kwargs: Any) -> None:
            self.value = value

        def is_type(self) -> bool:
            try:
                pathlib.Path(self.value)
            except Exception:
                return False
            else:
                return True

        def convert(self) -> Any:
            return pathlib.Path(self.value)

    type_affinity, converter = pathlib.Path, Path


class FileValidator(Validator):
    """A validator that can handle filesystem paths which are files. returns a pathmagic.File instance on Validator.convert()."""
    class File:
        def __init__(self, value: Any, *args: Any, **kwargs: Any) -> None:
            self.value = value

        def is_type(self) -> bool:
            if PathValidator().is_valid(self.value):
                return self.value is None or pathlib.Path(self.value).is_file()
            else:
                return False

        def convert(self) -> Any:
            return pathmagic.File(self.value)

    type_affinity, converter = pathmagic.File, File


class DirValidator(Validator):
    """A validator that can handle filesystem paths which are folders. returns a pathmagic.Dir instance on Validator.convert()."""
    class Dir:
        def __init__(self, value: Any, *args: Any, **kwargs: Any) -> None:
            self.value = value

        def is_type(self) -> bool:
            if PathValidator().is_valid(self.value):
                return self.value is None or pathlib.Path(self.value).is_dir()
            else:
                return False

        def convert(self) -> Any:
            return pathmagic.Dir(self.value)

    type_affinity, converter = pathmagic.Dir, Dir


class EnumValidator(ParametrizableValidator, Generic[E]):
    class Enum(Generic[E]):
        def __init__(self, value: Any, *args: Any, enum_: Type[E], **kwargs: Any) -> None:
            self.value = value
            self.enum = enum_

        def is_type(self) -> bool:
            try:
                self.convert()
                return True
            except KeyError:
                return False

        def convert(self) -> E:
            return self.enum[self.value]

    type_affinity, converter = enum.Enum, Enum

    def __class_getitem__(cls, param: Type[E]) -> EnumValidator.ParametrizedProxy:
        return super().__class_getitem__(param)

    def convert(self, value: Any) -> E:
        return super().convert(value)

    def parametrize(self, param: enum.Enum) -> EnumValidator:
        self.converter_kwargs["enum_"] = param
        return self


class Validate:
    """A class containing all known validators."""
    String, Boolean, Integer, Float, Decimal = StringValidator, BooleanValidator, IntegerValidator, FloatValidator, DecimalValidator
    DateTime, Date = DateTimeValidator, DateValidator
    List, Dict, Set = ListValidator, DictionaryValidator, SetValidator
    Path, File, Dir = PathValidator, FileValidator, DirValidator
    Enum = EnumValidator
    Anything, Unknown = AnythingValidator, UnknownTypeValidator

    @classmethod
    def infer_type(cls, type_: Any, **kwargs: Any) -> Validator:
        """Return a validator appropriate to the type_affinity passed."""
        if isinstance(type_, Validator):
            return type_
        elif type_ is None:
            return AnythingValidator(**kwargs)
        elif issubclass_safe(type_, Validator):
            return type_(**kwargs)
        else:
            if (validator := ValidatorMeta.registry.get(type_)) is not None:
                return validator(**kwargs)
            else:
                for validator_dtype, validator in ValidatorMeta.registry.items():
                    if issubclass_safe(type_, validator_dtype):
                        return validator(**kwargs)
                else:
                    return UnknownTypeValidator(constructor=type_, **kwargs)
