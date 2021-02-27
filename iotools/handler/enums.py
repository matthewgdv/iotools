from subtypes import Enum


class RunMode(Enum):
    """An Enum of the various run modes an ArgHandler accepts."""
    SMART, COMMANDLINE, GUI, PROGRAMMATIC = "smart", "commandline", "gui", "programmatic"
