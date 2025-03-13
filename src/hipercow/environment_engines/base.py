"""Support for environments.

This module provides the support needed to implement real environment
engines.  The functions and classes documented here are really for
internal use, but are needed for developing new environment types.  It
may be useful to consult the environment docs on the hipercow
documentation site alongside the documentation here.

"""

import platform
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from hipercow.root import Root


# We don't want to call actual 'platform' code very often because our
# intent is that we're generating things for another system.
@dataclass
class Platform:
    """Information about a platform.

    The most basic information about a platform that we need to set up
    an environment, derived from the the `platform` module.

    Attributes:
        system: The name of the system, in lowercase.  Values will be
            `linux`, `windows` or `darwin` (macOS).  We may replace
            this with an `Enum` in future.

        version: The python version, as a 3-element version string.

    """

    system: str
    version: str

    @staticmethod
    def local() -> "Platform":
        """Platform information for the running Python.

        A convenience function to construct suitable platform
        information for the currently running system.

        """
        return Platform(platform.system().lower(), platform.python_version())


class EnvironmentEngine(ABC):
    """Base class for environment engines.

    Attributes:
        root: The `hipercow` root
        name: The name of the environment to provision
        platform: Optionally, the platform to target.

    """

    def __init__(self, root: Root, name: str, platform: Platform | None = None):
        self.root = root
        self.name = name
        self.platform = platform or Platform.local()

    def exists(self) -> bool:
        """Test if an environment exists.

        This method is not abstract, and generally should not need to
        be replaced by derived classes.

        Returns:
            `True` if the environment directory exists, otherwise
            `False`.  Note that `True` does not mean that the
            environment is *usable*; this is mostly intended to be
            used to determine if `create()` needs to be called.

        """
        return self.path().exists()

    def path(self) -> Path:
        """Compute path to the environment contents.

        This base method version will return a suitable path within
        the root.  Implementations can use this path directly (say, if
        the environment path does not need to differ according to
        platform etc), or compute their own.  We might change the
        logic here in future to make this base-class returned path
        more generally useful.

        Returns:
            The path to the directory that will store the environment.

        """
        return self.root.path_environment_contents(self.name)

    @abstractmethod
    def create(self, **kwargs) -> None:
        """Create (or initialise) the environment.

        This method will be called on the target platform, not on the
        client platform.  Most environment systems have a concept of
        initialisation; this will typically create the directory
        referred to by `path()`, and do any required bootstrapping.
        It will not typically install anything for the user.

        In general, we expect `create()` to be called only once per
        environment lifetime, while `provision()` we expect to be
        called every time the environment is modified (one or many
        times).

        Args:
            **kwargs (Any): Additional keyword arguments passed on to
                the concrete method

        Returns:
            Nothing: Called for side-effects only.

        """
        pass  # pragma: no cover

    @abstractmethod
    def check_args(self, cmd: list[str] | None) -> list[str]:
        """Check arguments provided in `cmd` for suitability.

        This method runs on the client; the python process initiating
        the provisioning request, and does not run in the context of
        the process that will create the environment.  In particular,
        don't assume that the platform information is the same.

        Args:
            cmd: A list of arguments to provision an environment, or
                `None` if the user provided none.  In the latter case you
                must provide suitable defaults or error.

        Returns:
            A validated list of arguments.

        """
        pass  # pragma: no cover

    @abstractmethod
    def provision(self, cmd: list[str], **kwargs) -> None:
        """Provision an environment.

        Install packages or software into the environment.

        Args:
            cmd: A command to run in the environment.  Most of the
                time this just calls `hipercow.utils.subprocess_run`
                directly

            **kwargs (Any): Additional keyword arguments passed
                through to the concrete method.

        Returns:
            Nothing: Called for side-effects only.

        """
        pass  # pragma: no cover

    @abstractmethod
    def run(
        self,
        cmd: list[str],
        *,
        env: dict[str, str] | None = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """Run a command within an environment.

        Both provisioning and running tasks will run in their context
        of an environment.  This method must be specialised to
        activate the environment and then run the given shell command.

        This method should (eventually) call
        `hipercow.util.subprocess_run`, returning the value from that
        function.

        Args:
            cmd: The command to run

            env: An optional dictionary of environment variables that
                will be set within the environment.

            **kwargs (Any): Additional methods passed from the
                provisioner or the task runner.

        Return:
            Information about the completed process.  Note that
            errors are not thrown unless the keyword argument
            `check=True` is provided.

        """
        pass  # pragma: no cover
