# hipercow

This is a package for interfacing with the DIDE cluster directly from Python.  It is related to the [R package of the same name](https://mrc-ide.github.io/hipercow/) but with a focus on working with Python or other cli jobs.

## Installation

Installation will soon work through `pip`, with

```sh
pip install hipercow
```

in the meantime you can install from GitHub with

```sh
pip install git+https://github.com/mrc-ide/hipercow-py
```

You have several basic options to install:

1. Install into a virtual environment along with everything else
2. Install as a standalone tool with [pipx](https://pipx.pypa.io/stable/) so that `hipercow` is globally available but not part of your project dependencies
3. Install globally with `pip` (not recommended)
