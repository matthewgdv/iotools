from __future__ import annotations

import sys

from pathmagic import PathLike, Dir, File
from iotools.misc import IoToolsConfig, Config


class ClinkConfig(Config):
    name = "clink"
    default = {
        "active": False,
        "scripts": {}
    }


class ClinkIntegration:
    def __init__(self, clink_lua_folder: PathLike = None, python_interpreter_folder: PathLike = None) -> None:
        self.config = ClinkConfig(parent=IoToolsConfig())
        self.python_interpreter_folder = clink_lua_folder if clink_lua_folder is not None else File(sys.executable).parent

        self.clink_lua_folder = clink_lua_folder if clink_lua_folder is not None else Dir.from_appdata().new_dir("clink")
        self.lua = self.clink_lua_folder.new_file("python", "lua")

    def activate(self) -> ClinkIntegration:
        self.python_interpreter_folder.files["python.exe"].new_rename("pyscript", "exe")

        with self.config:
            self.config.data.active = True

        return self

    def deactivate(self) -> ClinkIntegration:
        self.python_interpreter_folder.new_file("pyscript.exe").delete()
        self.clear()
        return self

    def clear(self) -> ClinkIntegration:
        with self.config:
            self.config.clear()

        return self
