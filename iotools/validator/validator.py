from __future__ import annotations

import datetime as dt
from typing import Any, List, Callable
import pathlib
import enum
import copy

import typepy

from maybe import Maybe
from subtypes import DateTime, Enum
import pathmagic
from miscutils import issubclass_safe


class TypeConversionError(typepy.TypeConversionError):
    def __init__(self, validator: Validator, value: Any) -> None:
        super().__init__(f"Failed {'strict' if validator.strict else 'permissive'}, {'' if validator.nullable else 'non-'}nullable conversion of {repr(value)} (type {type(value).__name__}) to type {validator.converter.__name__}.")


class Condition:
    def __init__(self, condition: Callable[..., bool], name: str = None) -> None:
        self.condition, self.name = condition, name

    def __str__(self) -> str:
        return Maybe(self.name).else_(self.condition.__name__)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={repr(self.name)}, condition={self.condition.__name__})"

    def __call__(self, input_val: Any) -> bool:
        return self.condition(input_val)


class GenericMeta(type):
    def __getitem__(cls, key: Any) -> GenericMeta:
        newcls = copy.deepcopy(cls)
        newcls._default_generic_type = key
        return newcls


class Validator:
    dtype = None
    converter = None

    def __init__(self, *, nullable: bool = False, strict: bool = False, choices: enum.Enum = None) -> None:
        self.nullable = self.strict = None  # type: bool
        self.choices: list = None
        self.conditions: List[Condition] = []

        self.set_nullable(nullable).set_strict(strict)
        if choices is not None:
            self.set_choices(choices)

    def __repr__(self) -> str:
        return f"""{type(self).__name__}({", ".join([f"{attr}={repr(val) if not 'dtype' in attr else (None if val is None else val.__name__)}" for attr, val in self.__dict__.items() if not attr.startswith('_')])})"""

    def __call__(self, value: Any) -> Any:
        return self.convert(value)

    def set_nullable(self, nullable: bool = True) -> Validator:
        self.nullable = nullable
        return self

    def set_strict(self, strict: bool = True) -> Validator:
        self.strict = strict
        return self

    def set_choices(self, enumeration: enum.Enum) -> Validator:
        self.choices = [member.value for member in enumeration] if issubclass_safe(enumeration, enum.Enum) else list(enumeration)
        return self

    def add_condition(self, condition: Callable, name: str = None) -> Validator:
        self.conditions.append(Condition(condition=condition, name=name))
        return self

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return self.nullable

        if not self.converter(value, strict_level=typepy.StrictLevel.MAX if self.strict else typepy.StrictLevel.MIN).is_type():
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
                ret = self.converter(value, strict_level=typepy.StrictLevel.MAX if self.strict else typepy.StrictLevel.MIN).convert()
            except typepy.TypeConversionError:
                raise TypeConversionError(self, value)

            if self.choices is not None and ret not in self.choices:
                raise ValueError(f"Value '{value}' is not a valid choice. Valid choices are: {', '.join([repr(option) for option in self.choices])}.")

            for condition in self.conditions:
                if not condition(ret):
                    raise ValueError(f"Value '{value}' does not satisfy the condition: '{condition}'.")

            return ret

    def _try_eval(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = eval(value, {}, {})
            except Exception:
                pass

        return value


class AnythingValidator(Validator):
    class Anything:
        def __init__(self, value: Any, *args: Any, **kwargs: Any) -> Any:
            self.value = value

        def is_type(self) -> bool:
            return True

        def convert(self) -> Any:
            return self.value

    converter = Anything


class UnknownTypeValidator(Validator):
    converter = AnythingValidator.Anything

    def __init__(self, constructor: Any, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._constructor = constructor

    def convert(self, value) -> Any:
        return self._constructor(super().convert(value))


class BoolValidator(Validator):
    dtype = bool
    converter = typepy.Bool


class StringValidator(Validator):
    dtype = str
    converter = typepy.String

    def max_len(self, length: int) -> StringValidator:
        self.conditions.append(Condition(lambda val: len(val) <= length, name=f"len(val) <= {length}"))
        return self

    def min_len(self, length: int) -> StringValidator:
        self.conditions.append(Condition(lambda val: len(val) >= length, name=f"len(val) >= {length}"))
        return self


class IntegerValidator(Validator):
    dtype = int
    converter = typepy.Integer

    def max_value(self, value: int) -> IntegerValidator:
        self.conditions.append(Condition(lambda val: val <= value, name=f"val <= {value}"))
        return self

    def min_value(self, value: int) -> IntegerValidator:
        self.conditions.append(Condition(lambda val: val >= value, name=f"val >= {value}"))
        return self


class FloatValidator(Validator):
    dtype = float
    converter = typepy.RealNumber

    def max_value(self, value: float) -> FloatValidator:
        self.conditions.append(Condition(lambda val: val <= value, name=f"val <= {value}"))
        return self

    def min_value(self, value: float) -> FloatValidator:
        self.conditions.append(Condition(lambda val: val >= value, name=f"val >= {value}"))
        return self


class ListValidator(Validator, metaclass=GenericMeta):
    dtype = list
    converter = typepy.List
    _default_generic_type = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.val_dtype = self._default_generic_type

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

    def convert(self, value: Any) -> list:
        value = self._try_eval(value)

        converted = super().convert(value)

        if converted is None or self.val_dtype is None:
            return converted
        else:
            validator = Validate.Type(self.val_dtype, nullable=True)
            return [validator(item) for item in super().convert(value)]


class DictionaryValidator(Validator, metaclass=GenericMeta):
    dtype = dict
    converter = typepy.Dictionary
    _default_generic_type = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.key_dtype, self.val_dtype = Maybe(self._default_generic_type).else_((None, None))

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

    def convert(self, value: Any) -> dict:
        value = self._try_eval(value)

        converted = super().convert(value)

        if converted is None or (self.key_dtype is None and self.val_dtype is None):
            return converted
        else:
            converted = super().convert(value)
            key_validator, val_validator = Validate.Type(self.key_dtype, nullable=True), Validate.Type(self.val_dtype, nullable=True)
            return {key_validator(key): val_validator(val) for key, val in converted.items()}


class DateTimeValidator(Validator):
    dtype = dt.date
    converter = typepy.DateTime

    def before(self, date: dt.date) -> DateTimeValidator:
        self.conditions.append(Condition(condition=lambda val: val < date, name=f"val < {date}"))
        return self

    def after(self, date: dt.date) -> DateTimeValidator:
        self.conditions.append(Condition(condition=lambda val: val > date, name=f"val > {date}"))
        return self

    def convert(self, value) -> DateTime:
        converted = super().convert(value)
        return None if converted is None else DateTime.from_datetime(converted)


class PathValidator(Validator):
    dtype = pathlib.Path

    class Path:
        def __init__(self, value: Any, *args: Any, **kwargs: Any) -> Any:
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

    converter = Path


class FileValidator(Validator):
    dtype = pathmagic.File

    class File:
        def __init__(self, value: Any, *args: Any, **kwargs: Any) -> Any:
            self.value = value

        def is_type(self) -> bool:
            if PathValidator().is_valid(self.value):
                return self.value is None or pathlib.Path(self.value).is_file()
            else:
                return False

        def convert(self) -> Any:
            return pathmagic.File(self.value)

    converter = File


class DirValidator(Validator):
    dtype = pathmagic.Dir

    class Dir:
        def __init__(self, value: Any, *args: Any, **kwargs: Any) -> Any:
            self.value = value

        def is_type(self) -> bool:
            if PathValidator().is_valid(self.value):
                return self.value is None or pathlib.Path(self.value).is_dir()
            else:
                return False

        def convert(self) -> Any:
            return pathmagic.Dir(self.value)

    converter = Dir


class Validate(Enum):
    Int, Float, Bool, Str, List, Dict, DateTime = IntegerValidator, FloatValidator, BoolValidator, StringValidator, ListValidator, DictionaryValidator, DateTimeValidator
    Path, File, Dir = PathValidator, FileValidator, DirValidator

    @classmethod
    def Type(self, dtype: Any, **kwargs: Any) -> Validator:
        dtypes = {member.value.dtype: member.value for member in self}
        dtypes.update({None: AnythingValidator})
        validator = dtypes.get(dtype)

        if validator is not None:
            return validator(**kwargs)
        else:
            if issubclass_safe(dtype, Validator):
                return dtype(**kwargs)
            else:
                for key, val in dtypes.items():
                    if issubclass_safe(dtype, key):
                        return val(**kwargs)
                else:
                    return UnknownTypeValidator(constructor=dtype, **kwargs)
