from __future__ import annotations

import datetime as dt
from typing import Any, Union

from subtypes import DateTime, Str
from pathmagic import File, Dir


class TypeValidator:
    class UnknownTypeError(TypeError):
        pass

    def __init__(self, dtype: Any, coerce: bool = True, optional: bool = False) -> None:
        self.type, self.coerce, self.optional, self._valid = dtype, coerce, optional, False
        self._value: Any = None

        self.builtin_types: dict = {
            int: self.is_int_or_similar,
            float: self.is_float_or_similar,
            bool: self.is_bool_or_similar,
            str: self.is_str_or_similar,
            list: self.is_list_or_similar,
            dict: self.is_dict_or_similar,
            tuple: self.is_tuple_or_similar,
        }

        self.generic_types: dict = {
            list: self.is_typed_list,
            dict: self.is_typed_dict
        }

        self.custom_types: dict = {
            dt.date: self.is_date_or_similar,
            dt.datetime: self.is_date_or_similar,
            DateTime: self.is_date_or_similar,
            File: self.is_file_or_similar,
            Dir: self.is_dir_or_similar
        }

    def __bool__(self) -> bool:
        return self._valid

    def __call__(self, val: Any) -> Any:
        self.validate(val)
        return self.value

    @property
    def value(self) -> Any:
        if self:
            return self._value
        else:
            raise TypeError(f"{repr(self._value)} is '{self.get_type_name(type(self._value))}', and cannot be implicitly coerced to '{self.get_type_name(self.type)}'")

    def validate(self, val: Any) -> TypeValidator:
        self._value, self._valid = val, False

        if self.optional:
            if self._value is None:
                self._valid = True
                return self

        try:
            if self.type in self.builtin_types:
                handler = self.builtin_types[self.type]
            elif self.type.__module__ == "typing":
                handler = self.generic_types[self.type.__origin__]
            else:
                handler = self.custom_types[self.type]
        except KeyError:
            raise TypeValidator.UnknownTypeError(f"""dtype '{self.type}' not recognized. Must be: {", ".join([f"'{self.get_type_name(vartype)}'" for vartype in {**self.builtin_types, **self.generic_types, **self.custom_types}])}.""")

        handler()

        return self

    def is_int_or_similar(self) -> None:
        if isinstance(self._value, int):
            self._valid = True
        if not self.coerce:
            self._valid = False
        else:
            try:
                int(self._value)
            except (ValueError, TypeError):
                self._valid = False
            else:
                if float(self._value).is_integer():
                    self._valid, self._value = True, int(self._value)
                else:
                    self._valid = False

    def is_float_or_similar(self) -> None:
        if isinstance(self._value, float):
            self._valid = True
        if not self.coerce:
            self._valid = False
        else:
            try:
                float(self._value)
            except (ValueError, TypeError):
                self._valid = False
            else:
                self._valid, self._value = True, float(self._value)

    def is_bool_or_similar(self) -> None:
        if isinstance(self._value, bool):
            self._valid = True
        if not self.coerce:
            self._valid = False
        if isinstance(self._value, str):
            if self._value.strip().lower() in ["true", "t", "yes", "y"]:
                self._valid, self._value = True, True
            elif self._value.strip().lower() in ["false", "f", "no", "n"]:
                self._valid, self._value = True, False
        if isinstance(self._value, int):
            if self._value == 1:
                self._valid, self._value = True, True
            elif self._value == 0:
                self._valid, self._value = True, False
        else:
            self._valid = False

    def is_str_or_similar(self) -> None:
        if isinstance(self._value, str) or self.coerce:
            self._value, self._valid = self._value if isinstance(self._value, str) else str(self._value), True

    def is_list_or_similar(self) -> None:
        if isinstance(self._value, list):
            self._valid = True
        else:
            if not self.coerce:
                self._valid = False
            else:
                if isinstance(self._value, str):
                    try:
                        self._value = eval(self._value, {}, {})
                    except (SyntaxError, NameError):
                        return
                elif hasattr(self._value, "__iter__"):
                    self._value = list(self._value)

                self._valid = True if isinstance(self._value, list) else False

    def is_tuple_or_similar(self) -> None:
        if isinstance(self._value, tuple):
            self._valid = True
        else:
            if not self.coerce:
                self._valid = False
            else:
                if isinstance(self._value, str):
                    try:
                        self._value = eval(self._value, {}, {})
                    except (SyntaxError, NameError):
                        return
                elif hasattr(self._value, "__iter__"):
                    self._value = tuple(list(self._value))

                self._valid = True if isinstance(self._value, tuple) else False

    def is_dict_or_similar(self) -> None:
        if isinstance(self._value, dict):
            self._valid = True
        else:
            if not self.coerce:
                self._valid = False
            else:
                if isinstance(self._value, str):
                    try:
                        self._value = eval(self._value, {}, {})
                    except (SyntaxError, NameError):
                        return

                self._valid = True if isinstance(self._value, dict) else False

    def is_date_or_similar(self) -> None:
        def datetime_from_valid(val: Union[DateTime, dt.datetime, dt.date]) -> DateTime:
            return DateTime.from_date(val) if isinstance(val, dt.date) else DateTime.from_datetime(val)

        if any([isinstance(self._value, dtype) for dtype in (DateTime, dt.datetime, dt.date)]):
            self._value = datetime_from_valid(self._value)
            self._valid = True
        else:
            if not self.coerce:
                self._valid = False
            else:
                if isinstance(self._value, str):
                    try:
                        self._value = DateTime.fromisoformat(self._value)
                        self._valid = True
                    except (SyntaxError, NameError):
                        try:
                            self._value = datetime_from_valid(eval(self._value, {}, {}))
                            self._valid = True
                        except (SyntaxError, NameError):
                            return

    def is_typed_list(self) -> None:
        self.is_list_or_similar()
        if self and len(self.type.__args__) == 1 and self.type.__args__[0] in self.builtin_types:
            sub_validators = [TypeValidator(dtype=self.type.__args__[0], coerce=self.coerce).validate(item) for item in self._value]
            self._valid = all(sub_validators)
            self._value = [val.value for val in sub_validators] if self else self._value

    def is_typed_dict(self) -> None:
        self.is_dict_or_similar()
        if self and len(self.type.__args__) == 2 and all([arg in self.builtin_types for arg in self.type.__args__]):
            keys, vals = zip(*[(TypeValidator(dtype=self.type.__args__[0], coerce=self.coerce).validate(key), TypeValidator(dtype=self.type.__args__[1], coerce=self.coerce).validate(val))
                               for key, val in self._value.items()])
            self._valid = all(keys) and all(vals)
            self._value = {key.value: val.value for key, val in zip(keys, vals)} if self else self._value

    def is_file_or_similar(self) -> None:
        if isinstance(self._value, File):
            self._valid = True
        else:
            if not self.coerce:
                self._valid = False
            else:
                try:
                    self._value = File(self._value)
                    self._valid = True
                except (FileExistsError, PermissionError, TypeError):
                    self._valid = False

    def is_dir_or_similar(self) -> None:
        if isinstance(self._value, Dir):
            self._valid = True
        else:
            if not self.coerce:
                self._valid = False
            else:
                try:
                    self._value = Dir(self._value)
                    self._valid = True
                except (FileExistsError, PermissionError, TypeError):
                    self._valid = False

    @staticmethod
    def get_type_name(vartype: type) -> str:
        if hasattr(vartype, "__name__"):
            return vartype.__name__
        else:
            vartype_repr = repr(vartype)
            return Str(vartype_repr).after_last(r"\.")
