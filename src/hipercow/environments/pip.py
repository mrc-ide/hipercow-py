from dataclasses import dataclass
from pathlib import Path
import platform
from typing import Self

from hipercow.environments.base import Environment

# There are really two bits here - one to create a virtualenv, and the
# other to add things to it.  We mix them together here for now but
# we'll likely change this later.  We also need to consider things
# like which python versions are being invoked and that's not totally
# straightforward.
#
# We'll likely end up with something pretty similar for conda I
# imagine?  We might need to distinguish between (mini)?(conda|mamba)
# but it's not clear how much these differences matter to most
#
# Finally, we might have software made available globally - these are
# the modules in the linux version and outr batch files in windows.
# Probably these will represent only a small subset of software
# though, mostly concerned with bootstrapping. We should check with
# bioinformatics users about preferences for installing tools via
# conda vs having them available (e.g., via easybuild).  My guess is
# the former though.
@dataclass
class PipSource:
    mode: str
    data: dict[str, str]
    args: list[str]

    @staticmethod
    def requirements(path: str="requirements.txt") -> Self:
        data = {"path": path}
        return PipSource("requirements", data, ["pip", "install", "-r", path])

    @staticmethod
    def path(path: str=".") -> Self:
        data = {"path": path}
        return PipSource("path", data, ["pip", "install", path])

    def __str__(self) -> str:
        data_str = ", ".join(f"{k}={v}" for k, v in self.data.items())
        return f"{self.mode}: {data_str}"


class PipVenv(Environment):
    # Additional args here might be useful, especially 'clear' and
    # 'copies', but these might make most sense on the *initial* setup
    # (or on a particular setup) rather than being fixed into the
    # definition.
    #
    # Similarly, there are args here, such as --dry-run,
    # --upgrade-strategy, and -e which are going to be hard to sort
    # out.  Let's do a single one for now and then we'll allow for
    # arbitrary subsequent installation _into_ an environment.
    #
    # We'll need to broaden this to accept additional pip cli args,
    # most likely, and we could eventually support a series of
    # commands. I did try that way first but it's hard to get through
    # the cli interface, and so probably needs thinking about more
    # carefully, really.
    def __init__(self, *, requirements: str | None=None, path: str | None=None):
        self._source = _pip_source(requirements=requirements, path=path)

    def describe(self):
        print(f"Pip installation:")
        print(self._source)

    def path(self, name: str) -> Path:
        return (
            Path("venv") /
            platform.system().lower() /
            platform.python_version() /
            name
        )

    def create(self, name: str) -> list[str]:
        # We could use venv or virtualenv here, they are the same but
        # different in classic python packaging style.
        # https://virtualenv.pypa.io/en/latest/index.html
        #
        # One downside of venv is that it does not include a script
        # for windows; we will need to check on the cluster versions
        # what to use here, and we might need to write out a suitable
        # hand-written file if it does not get installed by default.
        # We do get a powershell script at least...
        path = str(self.path(name))
        return ["python", "-m", "venv", path]

    def activate(self, name: str, platform: str) -> list[str]:
        p = self.path(name)
        if platform == "windows":
            return ["call", str(p / "Scripts" / "activate.bat")]
        else:
            return [".", str(p / "bin" / "activate")]

    def install(self) -> list[str]:
        return self._source.args


# This will probably need considerable tweaking over time, but it
# should do for now.
def _pip_source(**kwargs):
    given = {k: v for k, v in kwargs.items() if v is not None}
    if len(given) == 0:
        msg = "Missing option to install from pip"
        raise Exception(msg)
    if len(given) > 1:
        msg = "More than one option provided to install from pip"
        raise Exception(msg)
    mode, value = given.popitem()
    if mode == "requirements":
        return PipSource.requirements(value)
    else:
        return PipSource.path(value)
