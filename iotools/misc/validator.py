from __future__ import annotations

import datetime as dt
from typing import Any, Union, List, Callable, Iterable, Optional, Type
import pathlib
import enum
import copy
import decimal

import typepy

from maybe import Maybe
from subtypes import DateTime, Date, Str, List, Dict
import pathmagic
from miscutils import issubclass_safe, get_short_lambda_source


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
        return Str(get_short_lambda_source(self.condition)).slice.after_first(r":").strip() if self.condition.__name__ == "<lambda>" else self.condition.__name__


class ValidatorMeta(type):
    registry = {}

    def __init__(cls: Type[Validator], name: str, bases: tuple, namespace: dict) -> None:
        if cls.dtype is not None:
            cls.registry[cls.dtype] = cls


class TypedCollectionMeta(ValidatorMeta):
    """A metaclass to drive the use of customizable validators for typed collections."""

    def __getitem__(cls, key: Any) -> TypedCollectionMeta:
        newcls = copy.deepcopy(cls)
        newcls._default_generic_type = key
        return newcls


class Validator(metaclass=ValidatorMeta):
    """Abstract validator class providing the interface for concrete validators. The most important methods are Validator.is_valid() and Validator.convert()."""
    dtype = None
    converter = None

    def __init__(self, *, nullable: bool = False, choices: Union[enum.Enum, Iterable] = None, use_subtypes: bool = True) -> None:
        self.nullable, self.use_subtypes = nullable, use_subtypes
        self.choices: Optional[set] = None
        self.conditions: list[Condition] = []

        if choices is not None:
            self.set_choices(choices)

    def __repr__(self) -> str:
        return f"""{type(self).__name__}({", ".join([f"{attr}={repr(val) if not 'dtype' in attr else (None if val is None else val.__name__)}" for attr, val in self.__dict__.items() if not attr.startswith('_')])})"""

    def __str__(self) -> str:
        return self.converter.__name__

    def __call__(self, value: Any) -> Any:
        return self.convert(value)

    def set_nullable(self, nullable: bool = True) -> Validator:
        self.nullable = nullable
        return self

    def set_choices(self, enumeration: Union[enum.Enum, Iterable]) -> Validator:
        self.choices = [member.value for member in enumeration] if issubclass_safe(enumeration, enum.Enum) else list(enumeration)
        return self

    def add_condition(self, condition: Callable, name: str = None) -> Validator:
        self.conditions.append(Condition(condition=condition, name=name))
        return self

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return bool(self.nullable)

        if not self.converter(value, strict_level=typepy.StrictLevel.MIN).is_type():
            return False

        try:
            self.convert(value)
        except (ValueError, TypeConversionError):
            return False
        else:
            return True

    def convert(self, value: Any) -> Any:
        if value is None:
            if self.nullable:
                return None
            else:
                raise TypeConversionError(self, value)
        else:
            try:
                ret = self.converter(value, strict_level=typepy.StrictLevel.MIN).convert()
            except typepy.TypeConversionError:
                raise TypeConversionError(self, value)

            if self.choices is not None and ret not in self.choices:
                raise ValueError(f"Value '{value}' is not a valid choice. Valid choices are: {', '.join([repr(option) for option in self.choices])}.")

            for condition in self.conditions:
                if not condition(ret):
                    raise ValueError(f"Value '{value}' does not satisfy the condition: '{condition}'.")

            return self._to_subtype(ret) if self.use_subtypes else ret

    def _to_subtype(self, value: Any) -> Any:
        return value

    def _try_eval(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = eval(value, {}, {})
            except Exception:
                pass

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
    dtype, converter = bool, typepy.Bool
    converter.__name__ = "Boolean"


class StringValidator(Validator):
    """A validator that can handle strings."""
    dtype, converter = str, typepy.String

    def max_len(self, length: int) -> StringValidator:
        self.conditions.append(Condition(lambda val: len(val) <= length, name=f"len(val) <= {length}"))
        return self

    def min_len(self, length: int) -> StringValidator:
        self.conditions.append(Condition(lambda val: len(val) >= length, name=f"len(val) >= {length}"))
        return self

    def _to_subtype(self, value: str) -> Str:
        return Str(value)


class IntegerValidator(Validator):
    """A validator that can handle integers."""
    dtype, converter = int, typepy.Integer

    def max_value(self, value: int) -> IntegerValidator:
        self.conditions.append(Condition(lambda val: val <= value, name=f"val <= {value}"))
        return self

    def min_value(self, value: int) -> IntegerValidator:
        self.conditions.append(Condition(lambda val: val >= value, name=f"val >= {value}"))
        return self


class RealNumberValidator(Validator):
    """A validator that can handle real numbers."""
    dtype, converter = float, typepy.RealNumber

    def max_value(self, value: float) -> RealNumberValidator:
        self.conditions.append(Condition(lambda val: val <= value, name=f"val <= {value}"))
        return self

    def min_value(self, value: float) -> RealNumberValidator:
        self.conditions.append(Condition(lambda val: val >= value, name=f"val >= {value}"))
        return self


class FloatValidator(RealNumberValidator):
    """A validator that can handle floating points numbers."""
    class Float(typepy.RealNumber):
        def convert(self) -> float:
            return float(super().convert())

    dtype, converter = float, Float


class DecimalValidator(RealNumberValidator):
    """A validator that can handle decimal numbers."""
    class Decimal(typepy.RealNumber):
        pass

    dtype, converter = decimal.Decimal, typepy.RealNumber


class ListValidator(Validator, metaclass=TypedCollectionMeta):
    """A validator that can handle lists. Item access can be used to create a new validator class that will also validate the type of the list members."""
    dtype, converter, _default_generic_type = list, typepy.List, None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.val_dtype = self._default_generic_type

    def __str__(self) -> str:
        return f"""{super().__str__()}{f"[{self._default_generic_type.__name__}]" if self._default_generic_type is not None else ""}"""

    def __getitem__(self, key) -> ListValidator:
        return self.of_type(key)

    def of_type(self, dtype: Any) -> ListValidator:
        self.val_dtype = dtype
        return self

    def is_valid(self, value: Any) -> bool:
        value = self._try_eval(value)

        if self.val_dtype is None:
            return super().is_valid(value)
        else:
            if super().is_valid(value):
                validator = Validate.Type(self.val_dtype, nullable=True)
                return all([validator.is_valid(item) for item in super().convert(value)])
            else:
                return False

    def convert(self, value: Any) -> Optional[list]:
        value = self._try_eval(value)

        converted = super().convert(value)

        if converted is None or self.val_dtype is None:
            return converted
        else:
            validator = Validate.Type(self.val_dtype, nullable=True)
            return [validator(item) for item in super().convert(value)]

    def _to_subtype(self, value: list) -> List:
        return List(value)


class SetValidator(ListValidator):
    """A validator that can handle floating points numbers."""
    class Set(typepy.List):
        def convert(self) -> set:
            return set(super().convert())

    dtype, converter, _default_generic_type = set, Set, None


class DictionaryValidator(Validator, metaclass=TypedCollectionMeta):
    """A validator that can handle dicts. Item access can be used to create a new validator class that will also validate the type of the dict's keys and values."""
    dtype, converter, _default_generic_type = dict, typepy.Dictionary, None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.key_dtype, self.val_dtype = self._default_generic_type or (None, None)

    def __str__(self) -> str:
        return f"""{super().__str__()}{f"[{', '.join([val.__name__ for val in self._default_generic_type])}]" if self._default_generic_type is not None else ""}"""

    def __getitem__(self, key) -> DictionaryValidator:
        key_dtype, val_dtype = key
        return self.of_types(key_dtype=key_dtype, val_dtype=val_dtype)

    def of_types(self, key_dtype: Any, val_dtype: Any) -> DictionaryValidator:
        self.key_dtype, self.val_dtype = key_dtype, val_dtype
        return self

    def is_valid(self, value: Any) -> bool:
        value = self._try_eval(value)

        if self.key_dtype is None and self.val_dtype is None:
            return super().is_valid(value)
        else:
            if super().is_valid(value):
                converted = super().convert(value)
                key_validator, val_validator = Validate.Type(self.key_dtype, nullable=True), Validate.Type(self.val_dtype, nullable=True)
                return all([key_validator.is_valid(item) for item in converted.keys()]) and all([val_validator.is_valid(item) for item in converted.values()])
            else:
                return False

    def convert(self, value: Any) -> Optional[dict]:
        value = self._try_eval(value)

        converted = super().convert(value)

        if converted is None or (self.key_dtype is None and self.val_dtype is None):
            return converted
        else:
            converted = super().convert(value)
            key_validator, val_validator = Validate.Type(self.key_dtype, nullable=True), Validate.Type(self.val_dtype, nullable=True)
            return {key_validator(key): val_validator(val) for key, val in converted.items()}

    def _to_subtype(self, value: dict) -> Dict:
        return Dict(value)


class DateTimeValidator(Validator):
    """A validator that can handle datetimes. Returns a subtypes.DateTime instance on Validator.convert(). If a datetime.datetime object is desired, call DateTime.to_datetime()."""
    dtype, converter = dt.datetime, typepy.DateTime

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
        def convert(self) -> float:
            datetime = super().convert()
            return dt.date(datetime.year, datetime.month, datetime.day)

    dtype, converter = dt.date, Date

    def _to_subtype(self, value: dt.datetime) -> DateTime:
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

    dtype, converter = pathlib.Path, Path


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

    dtype, converter = pathmagic.File, File


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

    dtype, converter = pathmagic.Dir, Dir


class Validate:
    """A class containing all known validators."""
    String, Boolean, Integer, Float, Decimal = StringValidator, BooleanValidator, IntegerValidator, FloatValidator, DecimalValidator
    DateTime, Date = DateTimeValidator, DateValidator
    List, Dict, Set = ListValidator, DictionaryValidator, SetValidator
    Path, File, Dir = PathValidator, FileValidator, DirValidator
    Anything, Unknown = AnythingValidator, UnknownTypeValidator

    @classmethod
    def Type(cls, dtype: Any, **kwargs: Any) -> Validator:
        """Return a validator appropriate to the dtype passed."""
        if dtype is None:
            return AnythingValidator(**kwargs)
        elif issubclass_safe(dtype, Validator):
            return dtype(**kwargs)
        else:
            if (validator := ValidatorMeta.registry.get(dtype)) is not None:
                return validator(**kwargs)
            else:
                for validator_dtype, validator in ValidatorMeta.registry.items():
                    if issubclass_safe(dtype, validator_dtype):
                        return validator(**kwargs)
                else:
                    return UnknownTypeValidator(constructor=dtype, **kwargs)
