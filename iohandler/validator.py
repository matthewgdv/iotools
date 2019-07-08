from __future__ import annotations

import datetime as dt
import functools
from typing import Any, List, Callable, TypeVar, cast
from pathlib import Path

import typepy

from maybe import Maybe
from subtypes import DateTime
from pathmagic import File, Dir

FuncSig = TypeVar("FuncSig", bound=Callable)


def _handle_nullability(func: FuncSig) -> FuncSig:
    @functools.wraps(func)
    def wrapper(*args: Any) -> Any:
        instance, value = args

        if value is None:
            if instance._nullable:
                return None
            else:
                raise TypeError(f"Expected {instance.validator.__name__}, got {type(value).__name__}.")
        else:
            return func(*args)
    return cast(FuncSig, wrapper)


class UnknownTypeError(TypeError):
    pass


class Condition:
    def __init__(self, condition: Callable[..., bool], name: str = None) -> None:
        self.condition, self.name = condition, name

    def __call__(self, input_val: Any) -> bool:
        return self.condition(input_val)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({Maybe(self.condition).__name__.else_(self.name)})"


class Validator:
    validator = None

    def __init__(self) -> None:
        self._nullable = False
        self._strict = typepy.StrictLevel.MIN
        self.conditions: List[Condition] = []

    def __call__(self, value: Any) -> Any:
        return self.convert(value=value)

    def nullable(self, nullable: bool = True) -> Validator:
        self._nullable = nullable
        return self

    def strict(self, strict: bool = True) -> BoolValidator:
        self._strict = typepy.StrictLevel.MAX if strict else typepy.StrictLevel.MIN
        return self

    @_handle_nullability
    def is_valid(self, value: Any) -> bool:
        return self.validator(value, strict_level=self._strict).is_type()

    @_handle_nullability
    def convert(self, value: Any) -> Any:
        return self.validator(value, strict_level=self._strict).convert()


class BoolValidator(Validator):
    validator = typepy.Bool


class StringValidator(Validator):
    validator = typepy.String

    def max_len(self, length: int) -> StringValidator:
        self.conditions.append(Condition(lambda val: len(val) <= length, name=f"len(val) <= {length}"))
        return self

    def min_len(self, length: int) -> StringValidator:
        self.conditions.append(Condition(lambda val: len(val) >= length, name=f"len(val) >= {length}"))
        return self


class IntegerValidator(Validator):
    validator = typepy.Integer

    def max_value(self, value: int) -> IntegerValidator:
        self.conditions.append(Condition(lambda val: val <= value, name=f"val <= {value}"))
        return self

    def min_value(self, value: int) -> IntegerValidator:
        self.conditions.append(Condition(lambda val: val >= value, name=f"val >= {value}"))
        return self


class FloatValidator(Validator):
    validator = typepy.RealNumber

    def max_value(self, value: float) -> FloatValidator:
        self.conditions.append(Condition(lambda val: val <= value, name=f"val <= {value}"))
        return self

    def min_value(self, value: float) -> FloatValidator:
        self.conditions.append(Condition(lambda val: val >= value, name=f"val >= {value}"))
        return self


class ListValidator(Validator):
    validator = typepy.List

    def __getitem__(self, key) -> ListValidator:
        return self.of_type(key)

    def of_type(self, dtype: Any) -> ListValidator:
        self.conditions.append(Condition(condition=lambda val: all([Validate.type(dtype).is_valid(item) for item in val]), name=f"List contents must be type: {dtype.__name__}"))
        return self


class DictionaryValidator(Validator):
    validator = typepy.Dictionary

    def __getitem__(self, key) -> ListValidator:
        key_dtype, val_dtype = key
        return self.of_types(key_dtype=key_dtype, val_dtype=val_dtype)

    def of_types(self, key_dtype: Any, val_dtype: Any) -> ListValidator:
        self.conditions.append(Condition(condition=lambda val: all([Validate.type(key_dtype).is_valid(item) for item in val]), name=f"Dict keys must be type: {key_dtype.__name__}"))
        self.conditions.append(Condition(condition=lambda val: all([Validate.type(val_dtype).is_valid(item) for item in val]), name=f"Dict values must be type: {val_dtype.__name__}"))
        return self


class DateTimeValidator(Validator):
    validator = typepy.DateTime

    def before(self, date: dt.date) -> DateTimeValidator:
        self.conditions.append(Condition(condition=lambda val: val < date, name=f"val < {date}"))
        return self

    def after(self, date: dt.date) -> DateTimeValidator:
        self.conditions.append(Condition(condition=lambda val: val > date, name=f"val > {date}"))
        return self

    def convert(self, value) -> DateTime:
        return DateTime.from_datetime(super().convert(value))


class PathValidator(Validator):
    validator = Path

    @_handle_nullability
    def is_valid(self, value: Any) -> bool:
        try:
            Path(value)
        except Exception:
            return False
        else:
            return True

    @_handle_nullability
    def convert(self, value: Any) -> Any:
        return self.validator(value)


class FileValidator(PathValidator):
    validator = File

    def is_valid(self, value: Any) -> bool:
        if super().is_valid(value):
            if value is None or Path(value).is_file():
                return True
        else:
            return False


class DirValidator(PathValidator):
    validator = Dir

    def is_valid(self, value: Any) -> bool:
        if super().is_valid(value):
            if value is None or Path(value).is_dir():
                return True
        else:
            return False


class Validate:
    _types = {
        int: IntegerValidator,
        float: FloatValidator,
        bool: BoolValidator,
        str: StringValidator,
        list: ListValidator,
        dict: DictionaryValidator,
        dt.date: DateTimeValidator,
        Path: PathValidator,
        File: FileValidator,
        Dir: DirValidator,
    }

    def Type(self, dtype: Any) -> Validator:
        validator = self._types.get(dtype)

        if validator is None:
            for key, val in self._types.items():
                if issubclass(dtype, key):
                    validator = val

        return dtype if validator is None else validator()

    @property
    def Bool(self) -> BoolValidator:
        return BoolValidator()

    @property
    def String(self) -> StringValidator:
        return StringValidator()

    @property
    def Int(self) -> IntegerValidator:
        return IntegerValidator()

    @property
    def Float(self) -> FloatValidator:
        return FloatValidator()

    @property
    def List(self) -> ListValidator:
        return ListValidator()

    @property
    def Dict(self) -> DictionaryValidator:
        return DictionaryValidator()

    @property
    def DateTime(self) -> DateTimeValidator:
        return DateTimeValidator()

    @property
    def Path(self) -> PathValidator:
        return PathValidator()

    @property
    def File(self) -> FileValidator:
        return FileValidator()

    @property
    def Dir(self) -> DirValidator:
        return DirValidator()


validate = Validate()
