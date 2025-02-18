from pathlib import Path
import platform

from hipercow.root import root

class Environment:
    pass


# We'll need a name, creation, deletion, update, activation - all of
# these can be put into a base class, perhaps abstract

# We'll need to have our parent set up binaries for pip, python (and
# conda)

# Our environment that we create has a *name*, it's not clear if that
# sits here or in the parent.

# We also need to be careful about platform and version in building
# paths, because the assumptions that pip etc makes will be wrong.


class Pip(Environment):
    def __init__(self):
        pass

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
        return ["python", "-m", "venv", "--copies", path]

    def exists(self, name: str) -> bool:
        return self.path(name).exists()

    def activate(self, name: str, platform: str) -> list[str]:
        p = self.path(name)
        if platform == "windows":
            return ["call", str(p / "activate.bat")]
        else:
            return [".", str(p / "activate")]

    def install(self) -> list[str]:
        return ["pip", "install", "-r", "requirements.txt"]
