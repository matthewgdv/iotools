Overview
====================

Provides several utilities for handling I/O:

The `IOHandler` class
--------------------
* Api similar to `argparse.ArgumentParser()`, with `IOHandler.add_arg()` (equivalent to `ArgumentParser.add_argument()`) and `IOHandler.collect_input()`
  (equivalent to `ArgumentParser.parse_args()`, also returning a namespace with the arugment values)
* Uses argparse under-the-hood when processing commandline arguments, but with a custom-built help interface that is more readable (and way prettier!)
* When no commandline arguments are provided, it will programatically build a GUI to collect user input, with widgets picked base on the 'argtype' argument of `IOHandler.add_arg()`
* Can also be run programatically by providing the argument values directly to `IOHandler.collect_input()` as a `dict` of argument name-value pairs
* The `ArgumentParser.add_argument()` function takes arguments telling the IOHandler how to handle nullability, default values, implicit coercion to the right type, whether the
  argument is optional, and commandline aliases

The `Validate` class
--------------------
* An accessor class granting access to several Validator class through attribute access
* Currently supports type checking and implicit coercion of the input value to the following supported types (int, float, bool, str, list, dict, subtypes.DateTime, pathlib.Path,
  pathmagic.File, pathmagic.Dir)
* Its attributes are: `Validate.Int`, `Validate.Float`, `Validate.Bool`, `Validate.Str`, `Validate.List`, `Validate.Dict`, `Validate.DateTime`, `Validate.Path`,
  `Validate.File`, `Validate.Dir`

The `Validator` classes
--------------------
* Currently there are IntegerValidator, FloatValidator, BoolValidator, StringValidator, ListValidator, DictionaryValidator, DateTimeValidator, PathValidator,
  FileValidator, DirValidator
* Some of these validators are implemented as a wrapper over typepy, but the api is different
* Validators can handle nullability as desired, and, where there is an equivalent typepy checker, have strictness levels that can be set.
* Some validators have additional validation methods to check for values in valid ranges. For example: `Validate.Int().max_value(7).is_valid(9)` would return False.
* Additional conditions can be added to a validator by passing callbacks that return boolean values to `Validator.add_condition()`
* The validator can be reused for any number of values once initially set up.
* ListValidator and DictionaryValidator will coerce strings by using eval (safely), rather than coercing a string to a list by calling list() on it

The `Gui` class and its various template subclasses
--------------------
* Gui class and several template subclasses that can be used alongside the various `WidgetManager` objects to easily set up a GUI, with the exact internals of the
  underlying QT classes abstracted away behind a consistent API. Makes it very quick and easy to set up a simple GUI. Is a thin wrapper around PyQT5.
* `FormGui` class for quickly setting up forms
* `HTMLGui` class for Rendering HTML in a separate window
* `ProgressBarGui` class for wrapping iterables, which will display a progress bar in a separate window as the iterable is consumed

The `WidgetManager` class and its various widget subclasses
--------------------
* Currently supports the following widgets: Label, Button, Checkbox, CheckBar, DropDown, Entry, Text, FileSelect, DirSelect, Calendar, DateTimeEdit, HtmlDisplay, ProgressBar,
  Table, ListTable, DictTable
* Have a consistent API primarily using the properties `WidgetManager.active`, `WidgetManager.state`, `WidgetManager.text`, and `WidgetManager.parent`.

Installation
====================

To install use pip:

    $ pip install pyiotools


Or clone the repo:

    $ git clone https://github.com/matthewgdv/iotools.git
    $ python setup.py install


Usage
====================

Usage examples coming soon.

Contributing
====================

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.

You can contribute in many ways:

Report Bugs
--------------------

Report bugs at https://github.com/matthewgdv/iotools/issues

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
--------------------

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help wanted" is open to whoever wants to implement a fix for it.

Implement Features
--------------------

Look through the GitHub issues for features. Anything tagged with "enhancement" and "help wanted" is open to whoever wants to implement it.

Write Documentation
--------------------

The repository could always use more documentation, whether as part of the official docs, in docstrings, or even on the web in blog posts, articles, and such.

Submit Feedback
--------------------

The best way to send feedback is to file an issue at https://github.com/matthewgdv/iotools/issues.

If you are proposing a new feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions are welcome :)

Get Started!
--------------------

Before you submit a pull request, check that it meets these guidelines:

1.  If the pull request adds functionality, it should include tests and the docs should be updated. Write docstrings for any functions that are part of the external API, and add
    the feature to the README.md.

2.  If the pull request fixes a bug, tests should be added proving that the bug has been fixed. However, no update to the docs is necessary for bugfixes.

3.  The pull request should work for the newest version of Python (currently 3.7). Older versions may incidentally work, but are not officially supported.

4.  Inline type hints should be used, with an emphasis on ensuring that introspection and autocompletion tools such as Jedi are able to understand the code wherever possible.

5.  PEP8 guidelines should be followed where possible, but deviations from it where it makes sense and improves legibility are encouraged. The following PEP8 error codes can be
    safely ignored: E121, E123, E126, E226, E24, E704, W503

6.  This repository intentionally disallows the PEP8 79-character limit. Therefore, any contributions adhering to this convention will be rejected. As a rule of thumb you should
    endeavor to stay under 200 characters except where going over preserves alignment, or where the line is mostly non-algorythmic code, such as extremely long strings or function
    calls.
