from pathlib import Path

from hipercow.util import find_file_descend


def init(path: str | Path) -> None:
    path = Path(path)
    dest = path / "hipercow"
    if dest.exists():
        if dest.is_dir():
            print(f"hipercow already initialised at {path}")
        else:
            msg = (
                "Unexpected file 'hipercow' (rather than directory)"
                f"found at {path}"
            )
            raise Exception(msg)
    else:
        dest.mkdir(parents=True)
        print(f"Initialised hipercow at {path}")


class Root:
    def __init__(self, path: str | Path) -> None:
        path = Path(path)
        if not (path / "hipercow").is_dir():
            msg = f"Failed to open 'hipercow' root at {path}"
            raise Exception(msg)
        self.path = path


def open_root(path: None | str | Path = None) -> Root:
    root = find_file_descend("hipercow", path or Path.cwd())
    if not root:
        msg = f"Failed to find 'hipercow' from {path}"
        raise Exception(msg)
    return Root(root)
