from __future__ import annotations

from typing import Any

from subtypes import Dict
from pathmagic import PathLike, File, Dir
from miscutils import executed_within_user_tree

import iotools


class Config:
    """
    A config class that abstracts away the process of creating, reading from, and writing to, a json config file within an OS-appropriate appdata dir.
    The directory itself can be accessed through the 'Config.folder' attribute.
    The data held by the config file can be accessed through 'Config.data' attribute, holding a special kind of dictionary that allows its items to be accessed through attribute access.
    Any changes made to this dictionary will not be persisted until Config.save() is called. Config.save() is automatically called upon exiting when this class is used as a context manager.
    This class is intended to be subclassed and can be used simply by providing the 'Config.name' (string) and 'Config.default' (dict) class attributes.
    Alternatively, this class can be used directly and these can be provided as constructor arguments instead.
    """

    name: str = None
    default: dict = None

    parent: Config = None
    author: str = None
    systemwide: bool = None

    def __init__(self, name: str = None, author: str = None, default: dict = None, systemwide: bool = None, parent: Config = None) -> None:
        self.name, self.author, self.default, self.systemwide = name or self.name, author or self.author or "pythondata", default or self.default, systemwide or self.systemwide
        self.parent = parent

        if self.parent is None:
            self.root = self.folder = Dir.from_appdata(app_name=self.name, app_author=self.author, systemwide=self.systemwide if self.systemwide is not None else not executed_within_user_tree())
        else:
            self.root, self.folder = parent.root, parent.folder.new_dir(self.name)

        self.file = self.folder.new_file(name="config", extension="json")
        self.data: Dict = self.file.content or Dict(self.default or {})

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def __enter__(self) -> Config:
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        if ex_type is None:
            self.save()

    def clear(self) -> None:
        """Clear the the config data. Will not be persisted to the config file until .save() is called on this object."""
        self.data = Dict(self.default or {})

    def import_(self, path: PathLike) -> None:
        """Import the config file at the given path."""
        file = File.from_pathlike(path)

        if file.extension != "json":
            raise TypeError(f"Config file to import must be type 'json'.")

        self.data = file.content

    def export_as(self, path: PathLike) -> None:
        """Export the config file to the given path."""
        self.file.copy(path)

    def export_to(self, folder: PathLike) -> None:
        """Export the config file to the given directory, keeping its name ('config.json')."""
        self.file.copy_to(folder)

    def start(self) -> File:
        """Initialize the config file with the default application for json files."""
        return self.file.start()

    def save(self) -> None:
        """Persist the changes to the 'Config.data' attribute to the config file."""
        self.file.content = self.data


class IoToolsConfig(Config):
    name = iotools.__name__
