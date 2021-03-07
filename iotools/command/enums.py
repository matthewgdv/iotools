from subtypes import Enum


class RunMode(Enum):
    """An Enum of the various run modes an CommandHandler accepts."""
    SMART = COMMANDLINE = GUI = PROGRAMMATIC = Enum.Auto()
