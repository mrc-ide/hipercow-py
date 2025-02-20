import os
import pickle
import platform
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from hipercow.driver import load_driver
from hipercow.root import Root

# Soon, we'll have some concept of configuration for our environments
# - the engine (venv, conda etc) and possibly things like python
# versions eventually.  For now, we just have the directory, empty,
# and that's ok.

# Naming throughout here is a mess, I'll pop things into their own
# modules later probably.


# We don't want to call actual 'platform' code very often because our
# intent is that we're generating things for another system.
@dataclass
class Platform:
    system: str
    version: str

    @staticmethod
    def local() -> "Platform":
        return Platform(platform.system().lower(), platform.python_version())


class EnvironmentProvider(ABC):
    def __init__(self, root: Root, platform: Platform, name: str):
        self.root = root
        self.platform = platform
        self.name = name

    def exists(self) -> bool:
        return self.path().exists()

    @abstractmethod
    def path(self) -> Path:
        pass

    @abstractmethod
    def create(self) -> None:
        pass

    @abstractmethod
    def provision(self, cmd: list[str] | None) -> None:
        pass


class Pip(EnvironmentProvider):
    def __init__(self, root: Root, platform: Platform, name: str):
        super().__init__(root, platform, name)

    def path(self) -> Path:
        return (
            self.root.path_environment(self.name)
            / f"venv-{self.platform.system}-{self.platform.version}"
        )

    def _envvars(self) -> dict[str, str]:
        base = self.path()
        path_env = base / _venv_bin_dir(self.platform.system)
        path = f"{path_env}{os.pathsep}{os.environ["PATH"]}"
        return {"VIRTUAL_ENV": str(base), "PATH": path}

    def create(self) -> None:
        # do we need to specify the actual python version here, or do
        # we assume that we have the correct version?  If we check
        # that the version here matches that in self.platform we're ok.
        cmd = ["python", "-m", "venv", str(self.path())]

        # One advantage of *not* calling subprocess here is that it
        # will be easier to control where output goes I think, which
        # we will need for working out how to stream output
        # eventually.  Ignore that for now, and just chuck things at
        # stdout and stderr...
        subprocess.run(cmd, check=True)

    # I am not sure either of these are really desirable, because they
    # don't provide any way of controlling the installation. Things
    # that we might want to do include:
    #
    # * use multiple requirements files
    # * clean before install
    # * install in editable mode
    # * upgrade and upgrade strategy, force reinstall
    # * additional pypi index
    # * dry run?
    #
    # We also want the ability to run an arbitrary command here, which
    # we'd accept as a list of strings probably, run within the
    # environment
    #
    # So later we might support
    #
    # hipercow provision [--name default] [--auto]
    # hipercow provision [--name default] -- pip install .
    def _auto(self) -> list[str]:
        if Path("requirements.txt").exists():
            return ["pip", "install", "-r", "requirements.txt"]
        if Path("pyproject.toml").exists():
            return ["pip", "install", "."]
        msg = "Can't run determine install command"
        raise Exception(msg)

    def _check_args(self, cmd: list[str] | None) -> list[str]:
        if not cmd:
            return self._auto()
        if cmd[0] != "pip":
            msg = "Expected first element of 'cmd' to be 'pip'"
            raise Exception(msg)
        return cmd

    def provision(self, cmd: list[str] | None) -> None:
        env = self._envvars()
        args = self._check_args(cmd)
        subprocess.run(args, env=env, check=True)


@dataclass
class EnvironmentConfiguration:
    provider: str

    # As with elsewhere, we will need to avoid actually serialising
    # the instance itself and only the configuration. Ignore this for
    # now, even though this will create versioning headaches for us.
    def write(self, root: Root, name: str):
        with root.path_environment_config(name).open("wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def read(root: Root, name: str) -> "EnvironmentConfiguration":
        with root.path_environment_config(name).open("rb") as f:
            return pickle.load(f)


def provider(root: Root, platform: Platform, name: str) -> EnvironmentProvider:
    cfg = EnvironmentConfiguration.read(root, name)
    if cfg.provider != "pip":
        raise NotImplementedError()
    return Pip(root, platform, name)


def environment_create(root: Root, name: str, provider: str) -> None:
    path = root.path_environment(name)

    if not path.exists():
        if provider != "pip":
            msg = "Only the 'pip' provider is supported"
            raise Exception(msg)
        print(f"Creating environment '{name}'")
        EnvironmentConfiguration(provider).write(root, name)
    else:
        # TODO: validate that config is the same by reading and comparing
        # prev = EnvironmentConfiguration.read(name)
        print(f"Environment '{name}' already exists")


def environment_list(root: Root) -> list[str]:
    # We'll possibly always have the 'none' environment, which will
    # prevent any environment being selected?
    return [x.name for x in (root.path / "hipercow" / "environments").glob("*")]


def environment_provision(
    root: Root,
    name: str | None,
    cmd: list[str] | None,
    *,
    driver: str | None = None,
):
    if name is None:
        name = "default"
    path_config = root.path_environment_config(name)
    if not path_config.exists():
        msg = f"Environment '{name}' does not exist"
        raise Exception(msg)

    dr = load_driver(root, driver, allow_none=True)
    if dr is None:
        msg = "Can't provision, no driver configured"
        raise Exception(msg)
    dr.provision(root, name, cmd)


def _venv_bin_dir(system: str) -> str:
    return "Scripts" if system == "windows" else "bin"
