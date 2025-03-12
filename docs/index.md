# `hipercow`

This is a package for interfacing with the DIDE cluster directly from Python.  It is related to the [R package of the same name](https://mrc-ide.github.io/hipercow/) but with a focus on working with Python or other commandline-based jobs.

## Installation

Installation is possible using `pip`, with

```sh
pip install hipercow
```

If you need to use a prerelease version you can use:

```sh
pip install git+https://github.com/mrc-ide/hipercow-py
```

or to install from a branch use

```sh
pip install git+https://github.com/mrc-ide/hipercow-py@branch
```

## Practical installation

Installing from `pip` is just half the fun.  There are three reasonable options that you might want to explore:

You have several basic options to install:

1. Install into a virtual environment along with everything else
2. Install as a standalone tool with [`pipx`](https://pipx.pypa.io/stable/) so that `hipercow` is globally available but not part of your project dependencies
3. Install globally with `pip` (not recommended)

### Into your virtual environment

We assume that you have created a virtual environment with something along the lines of

```console
python -m venv env
. env/bin/activate # or env/Scripts/activate on Windows
```

However, if using the DIDE windows cluster you will be on a network share and this might hit some [issues with Python's virtual environment support](dide.md#working-on-a-network-share).

After this you can run

```console
pip install hipercow
```

and `hipercow` will be available in your project packages.

This is the **required method** if using hipercow programmatically; i.e., if you plan on importing hipercow from your Python code.

### With `pipx`

[`pipx`](https://pipx.pypa.io/stable/) is a tool for installing a Python package that provides a command line interface in a way that is globally accessible to a user, but without interfering with your system python packages or your project python packages.

If you have `pipx` installed you can run

```
pipx install hipercow
```

and then you should be able to run

```
hipercow --version
```

without error.  If `pipx` is not found, then you need to install it.  The [`pipx` page lists installation instructions for every platform](https://pipx.pypa.io/stable/#install-pipx).  **Pay attention to warnings** when installing `pipx` or `hipercow` with `pipx` as these list additional commands that you will need to run in order to find `hipercow`.  This is particularly the case on Windows.
