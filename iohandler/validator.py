from __future__ import annotations

import datetime as dt
from typing import Any, List, Callable
import pathlib

import typepy

from maybe import Maybe
from subtypes import DateTime
import pathmagic


class TypeConversionError(typepy.TypeConversionError):
    def __init__(self, validator: Validator, value: Any) -> None:
        super().__init__(f"Failed {'strict' if validator._strict else 'permissive'}, {'' if validator._nullable else 'non-'}nullable conversion of {repr(value)} (type {type(value).__name__}) to type {validator.validator.__name__}.")


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
    validator = None

    def __init__(self, nullable: bool = False, strict: bool = False) -> None:
        self._nullable = self._strict = None  # type: bool
        self.conditions: List[Condition] = []
        self.nullable(nullable).strict(strict)

    def __call__(self, value: Any) -> Any:
        return self.convert(value)

    def nullable(self, nullable: bool = True) -> Validator:
        self._nullable = nullable
        return self

    def strict(self, strict: bool = True) -> Validator:
        self._strict = typepy.StrictLevel.MAX if strict else typepy.StrictLevel.MIN
        return self

    def condition(self, condition: Callable, name: str = None) -> Validator:
        self.conditions.append(Condition(condition=condition, name=name))
        return self

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return self._nullable

        ret = self.validator(value, strict_level=self._strict).is_type()
        if not ret:
            return False

        for condition in self.conditions:
            if not condition(self(value)):
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
                ret = self.validator(value, strict_level=self._strict).convert()
            except typepy.TypeConversionError:
                raise TypeConversionError(self, value)

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

    validator = Anything


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
                validator = validate.Type(self.dtype).nullable()
                return all([validator.is_valid(item) for item in super().convert(value)])
            else:
                return False

    def convert(self, value: Any) -> list:
        value = self._try_eval(value)

        if self.dtype is None:
            return super().convert(value)
        else:
            validator = validate.Type(self.dtype).nullable()
            return [validator(item) for item in super().convert(value)]


class DictionaryValidator(Validator):
    validator = typepy.Dictionary

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
                key_validator, val_validator = validate.Type(Maybe(self.key_dtype).else_(anything)).nullable(), validate.Type(Maybe(self.val_dtype).else_(anything)).nullable()
                return all([key_validator.is_valid(item) for item in converted.keys()]) and all([val_validator.is_valid(item) for item in converted.values()])
            else:
                return False

    def convert(self, value: Any) -> dict:
        value = self._try_eval(value)

        if self.key_dtype is None and self.val_dtype is None:
            return super().convert(value)
        else:
            converted, anything = super().convert(value), AnythingValidator()
            key_validator, val_validator = validate.Type(Maybe(self.key_dtype).else_(anything)).nullable(), validate.Type(Maybe(self.val_dtype).else_(anything)).nullable()
            return {key_validator(key): val_validator(val) for key, val in converted.items()}


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

    validator = Path


class FileValidator(Validator):
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

    validator = File


class DirValidator(Validator):
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

    validator = Dir


class Validate:
    _types = {
        int: IntegerValidator,
        float: FloatValidator,
        bool: BoolValidator,
        str: StringValidator,
        list: ListValidator,
        dict: DictionaryValidator,
        dt.date: DateTimeValidator,
        pathlib.Path: PathValidator,
        pathmagic.File: FileValidator,
        pathmagic.Dir: DirValidator,
    }

    def Type(self, dtype: Any) -> Validator:
        validator = self._types.get(dtype)

        if validator is None:
            try:
                if issubclass(dtype, Validator):
                    validator = dtype
            except TypeError:
                pass

        if validator is None:
            for key, val in self._types.items():
                try:
                    if issubclass(dtype, key):
                        validator = val
                except TypeError:
                    pass

        return dtype if validator is None else validator()

    @property
    def Anything(self) -> AnythingValidator:
        return AnythingValidator()

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
