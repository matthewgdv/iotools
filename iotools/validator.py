from __future__ import annotations

import datetime as dt
from typing import Any, List, Callable
import pathlib
import enum

import typepy

from maybe import Maybe
from subtypes import DateTime, Enum
import pathmagic
from miscutils import issubclass_safe


class TypeConversionError(typepy.TypeConversionError):
    def __init__(self, validator: Validator, value: Any) -> None:
        super().__init__(f"Failed {'strict' if validator._strict else 'permissive'}, {'' if validator._nullable else 'non-'}nullable conversion of {repr(value)} (type {type(value).__name__}) to type {validator.converter.__name__}.")


class Condition:
    def __init__(self, condition: Callable[..., bool], name: str = None) -> None:
        self.condition, self.name = condition, name

    def __str__(self) -> str:
        return Maybe(self.name).else_(self.condition.__name__)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={repr(self.name)}, condition={self.condition.__name__})"

    def __call__(self, input_val: Any) -> bool:
        return self.condition(input_val)


class Validator:
    dtype = None
    converter = None

    def __init__(self, *, nullable: bool = False, strict: bool = False) -> None:
        self._nullable = self._strict = None  # type: bool
        self._choices: list = None
        self._conditions: List[Condition] = []
        self.nullable(nullable).strict(strict)

    def __call__(self, value: Any) -> Any:
        return self.convert(value)

    def nullable(self, nullable: bool = True) -> Validator:
        self._nullable = nullable
        return self

    def strict(self, strict: bool = True) -> Validator:
        self._strict = typepy.StrictLevel.MAX if strict else typepy.StrictLevel.MIN
        return self

    def choices(self, enumeration: enum.Enum) -> Validator:
        self._choices = [member.value for member in enumeration] if issubclass_safe(enumeration, enum.Enum) else list(enumeration)
        return self

    def condition(self, condition: Callable, name: str = None) -> Validator:
        self._conditions.append(Condition(condition=condition, name=name))
        return self

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return self._nullable

        ret = self.converter(value, strict_level=self._strict).is_type()
        if not ret:
            return False

        try:
            self.convert(value)
        except ValueError:
            return False
        else:
            return True

    def convert(self, value: Any) -> Any:
        if value is None:
            if self._nullable:
                return None
            else:
                raise TypeConversionError(self, value)
        else:
            try:
                ret = self.converter(value, strict_level=self._strict).convert()
            except typepy.TypeConversionError:
                raise TypeConversionError(self, value)

            if self._choices is not None and ret not in self._choices:
                raise ValueError(f"Value '{value}' is not a valid choice. Valid choices are: {', '.join([repr(option) for option in self._choices])}.")

            for condition in self._conditions:
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
        self._conditions.append(Condition(lambda val: len(val) <= length, name=f"len(val) <= {length}"))
        return self

    def min_len(self, length: int) -> StringValidator:
        self._conditions.append(Condition(lambda val: len(val) >= length, name=f"len(val) >= {length}"))
        return self


class IntegerValidator(Validator):
    dtype = int
    converter = typepy.Integer

    def max_value(self, value: int) -> IntegerValidator:
        self._conditions.append(Condition(lambda val: val <= value, name=f"val <= {value}"))
        return self

    def min_value(self, value: int) -> IntegerValidator:
        self._conditions.append(Condition(lambda val: val >= value, name=f"val >= {value}"))
        return self


class FloatValidator(Validator):
    dtype = float
    converter = typepy.RealNumber

    def max_value(self, value: float) -> FloatValidator:
        self._conditions.append(Condition(lambda val: val <= value, name=f"val <= {value}"))
        return self

    def min_value(self, value: float) -> FloatValidator:
        self._conditions.append(Condition(lambda val: val >= value, name=f"val >= {value}"))
        return self


class ListValidator(Validator):
    dtype = list
    converter = typepy.List

    def __init__(self) -> None:
        super().__init__()
        self.dtype = None

    def __getitem__(self, key) -> ListValidator:
        return self.of_type(key)

    def of_type(self, dtype: Any) -> ListValidator:
        self.dtype = dtype
        return self

    def is_valid(self, value: Any) -> bool:
        value = self._try_eval(value)

        if self.dtype is None:
            return super().is_valid(value)
        else:
            if super().is_valid(value):
                validator = Validate.Type(self.dtype).nullable()
                return all([validator.is_valid(item) for item in super().convert(value)])
            else:
                return False

    def convert(self, value: Any) -> list:
        value = self._try_eval(value)

        if self.dtype is None:
            return super().convert(value)
        else:
            validator = Validate.Type(self.dtype).nullable()
            return [validator(item) for item in super().convert(value)]


class DictionaryValidator(Validator):
    dtype = dict
    converter = typepy.Dictionary

    def __init__(self) -> None:
        super().__init__()
        self.key_dtype, self.val_dtype = (None, None)

    def __getitem__(self, key) -> ListValidator:
        key_dtype, val_dtype = key
        return self.of_types(key_dtype=key_dtype, val_dtype=val_dtype)

    def of_types(self, key_dtype: Any, val_dtype: Any) -> ListValidator:
        self.key_dtype, self.val_dtype = key_dtype, val_dtype
        return self

    def is_valid(self, value: Any) -> bool:
        value = self._try_eval(value)

        if self.key_dtype is None and self.val_dtype is None:
            return super().is_valid(value)
        else:
            if super().is_valid(value):
                converted, anything = super().convert(value), AnythingValidator()
                key_validator, val_validator = Validate.Type(Maybe(self.key_dtype).else_(anything)).nullable(), Validate.Type(Maybe(self.val_dtype).else_(anything)).nullable()
                return all([key_validator.is_valid(item) for item in converted.keys()]) and all([val_validator.is_valid(item) for item in converted.values()])
            else:
                return False

    def convert(self, value: Any) -> dict:
        value = self._try_eval(value)

        if self.key_dtype is None and self.val_dtype is None:
            return super().convert(value)
        else:
            converted, anything = super().convert(value), AnythingValidator()
            key_validator, val_validator = Validate.Type(Maybe(self.key_dtype).else_(anything)).nullable(), Validate.Type(Maybe(self.val_dtype).else_(anything)).nullable()
            return {key_validator(key): val_validator(val) for key, val in converted.items()}


class DateTimeValidator(Validator):
    dtype = dt.date
    converter = typepy.DateTime

    def before(self, date: dt.date) -> DateTimeValidator:
        self._conditions.append(Condition(condition=lambda val: val < date, name=f"val < {date}"))
        return self

    def after(self, date: dt.date) -> DateTimeValidator:
        self._conditions.append(Condition(condition=lambda val: val > date, name=f"val > {date}"))
        return self

    def convert(self, value) -> DateTime:
        return DateTime.from_datetime(super().convert(value))


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
    Int = IntegerValidator
    Float = FloatValidator
    Bool = BoolValidator
    Str = StringValidator
    List = ListValidator
    Dict = DictionaryValidator
    DateTime = DateTimeValidator
    Path = PathValidator
    File = FileValidator
    Dir = DirValidator

    @classmethod
    def Type(self, dtype: Any, **kwargs: Any) -> Validator:
        dtypes = {member.value.dtype: member.value for member in self}
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
