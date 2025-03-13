import subprocess
from pathlib import Path

from hipercow.environment_engines.base import EnvironmentEngine, Platform
from hipercow.root import Root
from hipercow.util import subprocess_run


class Empty(EnvironmentEngine):
    """The empty environment, into which nothing may be installed."""

    def __init__(self, root: Root, name: str, platform: Platform | None = None):
        super().__init__(root, name, platform)

    def exists(self) -> bool:
        """The empty environment always exists.

        Returns:
            `True`

        """
        return True

    def path(self) -> Path:
        """The path to the empty environment, which never exists.

        Returns:
           Never returns, but throws if called.
        """
        msg = "The empty environment has no path"
        raise Exception(msg)

    # These "unused argument" errors from ruff are probably a bug?
    def create(self, **kwargs) -> None:  # noqa: ARG002
        """Create the empty environment, which already exists.

        Returns:
            Never returns, but throws if called.
        """
        msg = "Can't create the empty environment!"
        raise Exception(msg)

    def check_args(self, cmd: list[str] | None) -> list[str]:
        """Check arguments to the empty environment, which must be empty.

        Args:
            cmd: A list or `None`, if the list is not empty an error is thrown.

        Returns:
            The empty list.
        """
        if not cmd:
            return []
        else:
            msg = "No arguments are allowed to the empty environment"
            raise Exception(msg)

    def provision(self, cmd: list[str], **kwargs) -> None:  # noqa: ARG002
        """Install packages into the empty environment, which is not allowed.

        Returns:
            Never returns, but throws if called.
        """
        msg = "Can't provision the empty environment!"
        raise Exception(msg)

    def run(
        self,
        cmd: list[str],
        *,
        env: dict[str, str] | None = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        return subprocess_run(cmd, env=env, **kwargs)
