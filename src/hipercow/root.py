import platform
from pathlib import Path

from hipercow.util import find_file_descend


def init(path: str | Path) -> None:
    path = Path(path)
    dest = path / "hipercow" / "py"

    if dest.is_dir():
        print(f"hipercow already initialised at {path}")
        return

    root = find_file_descend("hipercow", path)
    if root is not None:
        print(f"hipercow already initialised at {root} (found from {path})")

    if dest.exists() and not dest.is_dir():
        msg = (
            "Unexpected file 'hipercow/py' (rather than directory)"
            f"found at {path}"
        )
        raise Exception(msg)

    dest.mkdir(parents=True)
    _add_gitignore(dest.parent)
    print(f"Initialised hipercow at {path}")


class Root:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path_base().parent.is_dir():
            msg = f"Failed to open 'hipercow' root at {path}"
            raise Exception(msg)
        if not self.path_base().is_dir():
            msg = f"Failed to open non-python 'hipercow' root at {path}"
            raise Exception(msg)

    def path_base(self, *, relative: bool = False) -> Path:
        return (Path() if relative else self.path) / "hipercow" / "py"

    def path_task(self, task_id: str | None, *, relative: bool = False) -> Path:
        base = self.path_base(relative=relative)
        if task_id is None:
            return base / "tasks"
        return base / "tasks" / task_id[:2] / task_id[2:]

    def path_task_times(self, task_id: str) -> Path:
        return self.path_task(task_id) / "times"

    def path_task_data(self, task_id: str) -> Path:
        return self.path_task(task_id) / "data"

    def path_task_result(self, task_id: str) -> Path:
        return self.path_task(task_id) / "result"

    def path_task_log(self, task_id: str) -> Path:
        return self.path_task(task_id) / "log"

    def path_recent(self) -> Path:
        return self.path_base() / "recent"

    def path_configuration(self, name: str | None) -> Path:
        hostname = platform.node()
        return self.path_base() / "config" / hostname / (name or ".")

    def path_environment(
        self, name: str | None, *, relative: bool = False
    ) -> Path:
        base = self.path_base(relative=relative)
        return base / "env" / (name or ".")

    def path_environment_config(self, name: str) -> Path:
        return self.path_environment(name) / "config"

    def path_environment_contents(
        self, name: str, *, relative: bool = False
    ) -> Path:
        return self.path_environment(name, relative=relative) / "contents"

    def path_provision(
        self, name: str, id: str, *, relative: bool = False
    ) -> Path:
        return self.path_environment(name, relative=relative) / "provision" / id

    def path_provision_data(
        self, name: str, id: str, *, relative: bool = False
    ) -> Path:
        return self.path_provision(name, id, relative=relative) / "data"

    def path_provision_result(
        self, name: str, id: str, *, relative: bool = False
    ) -> Path:
        return self.path_provision(name, id, relative=relative) / "result"

    def path_provision_log(
        self, name: str, id: str, *, relative: bool = False
    ) -> Path:
        return self.path_provision(name, id, relative=relative) / "log"


def open_root(path: None | str | Path = None) -> Root:
    root = find_file_descend("hipercow", path or Path.cwd())
    if not root:
        msg = f"Failed to find 'hipercow' from {path}"
        raise Exception(msg)
    return Root(root)


def _add_gitignore(path: Path):
    dest = path / ".gitignore"
    if not dest.exists():
        with dest.open("w") as f:
            f.write("*\n")
