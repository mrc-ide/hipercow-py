import os
from contextlib import contextmanager
from pathlib import Path


def find_file_descend(filename, path):
    path = Path(path)
    root = Path(path.anchor)

    while path != root:
        attempt = path / filename
        if attempt.exists():
            return attempt.parent.resolve()
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


def file_create(path: str | Path) -> None:
    Path(path).open("a").close()
