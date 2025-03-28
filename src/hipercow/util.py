import csv
import os
import platform
import re
import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any


def find_file_descend(filename: str, path: str | Path) -> Path | None:
    path = Path(path)
    root = Path(path.anchor)

    while path != root:
        attempt = path / filename
        if attempt.exists():
            return attempt.parent
        path = path.parent

    return None


def relative_workdir(path: str | Path, base: None | str | Path = None) -> Path:
    return Path(path).relative_to(Path(base) if base else Path.cwd())


@contextmanager
def transient_working_directory(path):
    origin = os.getcwd()
    try:
        if path is not None:
            os.chdir(path)
        yield
    finally:
        if path is not None:
            os.chdir(origin)


@contextmanager
def transient_envvars(env: dict[str, str | None]) -> Iterator[None]:
    def _set_envvars(env):
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    prev = {k: os.environ.get(k) for k in env.keys()}
    try:
        _set_envvars(env)
        yield
    finally:
        _set_envvars(prev)


def file_create(path: str | Path) -> None:
    Path(path).open("a").close()


def subprocess_run(
    cmd,
    *,
    filename: Path | None = None,
    check=False,
    env: dict | None = None,
    **kwargs,
) -> subprocess.CompletedProcess:
    env = os.environ | (env or {})
    try:
        if filename is None:
            return subprocess.run(cmd, **kwargs, check=check, env=env)
        else:
            with filename.open("ab") as f:
                return subprocess.run(
                    cmd,
                    check=check,
                    env=env,
                    stderr=subprocess.STDOUT,
                    stdout=f,
                    **kwargs,
                )
    except FileNotFoundError as err:
        if check:
            raise err
        elif filename is None:
            print(err)
        else:
            with filename.open("a") as f:
                print(err, file=f)
        return subprocess.CompletedProcess(cmd, -1)


def check_python_version(
    version: str | None, valid: list[str] | None = None
) -> str:
    if valid is None:
        valid = ["3.10", "3.11", "3.12", "3.13"]
    if not version:
        v = ".".join(platform.python_version_tuple()[:2])
    else:
        m = re.match(r"^([0-9]+)\.([0-9]+)(\.[0-9]+)?$", version)
        if not m:
            msg = f"'{version}' does not parse as a valid version string"
            raise Exception(msg)
        v = ".".join(m.groups()[:2])
    if v not in valid:
        msg = f"Version '{version}' is not supported"
        raise Exception(msg)
    return v


def truthy_envvar(name: str) -> bool:
    value = os.environ.get(name)
    return value is not None and (value.lower() in {"1", "true"})


def read_file_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    with path.open() as f:
        return f.read()


def loop_while(fn: Callable[[], bool]) -> None:
    while True:
        if not fn():
            break


@dataclass
class Result:
    exception: Exception | None = None

    def __bool__(self) -> bool:
        return self.exception is None

    @staticmethod
    def ok() -> "Result":
        return Result()

    @staticmethod
    def err(exception: Exception) -> "Result":
        return Result(exception)


def expand_grid(data: dict) -> list[dict]:
    return [
        dict(zip(data.keys(), el, strict=False))
        for el in product(*data.values())
    ]


# Probably some more work here to get the name to str here?
def read_csv_to_dict(filename: str | Path) -> list[dict[str, Any]]:
    with Path(filename).open(newline="") as f:
        return list(csv.DictReader(f))


# We could make this more generic, but this changes syntax at 3.12
# https://mypy.readthedocs.io/en/stable/generics.html#generic-functions
def tabulate(x: list[str]) -> dict[str, int]:
    ret: dict[str, int] = {}
    for el in x:
        try:
            ret[el] += 1
        except KeyError:
            ret[el] = 1
    return ret
