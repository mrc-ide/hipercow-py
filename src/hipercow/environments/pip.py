from dataclasses import dataclass
from pathlib import Path
import platform
from typing import Self

from hipercow.environments.base import Environment


@dataclass
class PipSource:
    mode: str
    data: dict[str, str]
    args: list[str]

    @staticmethod
    def requirements(path: str="requirements.txt") -> Self:
        data = {"path": path}
        return PipSource("requirements", data, ["-r", path])

    @staticmethod
    def path(path: str=".") -> Self:
        data = {"path": path}
        return PipSource("path", data, [path])

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
    def __init__(self, sources: PipSource | list[PipSource]):
        if isinstance(sources, PipSource):
            sources = [sources]
        elif len(sources) == 0:
            msg = "At least one source required"
            raise Exception(msg)
        self._sources = sources

    def describe(self):
        print("Pip installation:")
        for el in self._sources:
            print(str(el))

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

    def install(self) -> list[list[str]]:
        return [["pip", "install"] + el.args for el in self._sources]
