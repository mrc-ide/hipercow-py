import os
import subprocess
from contextlib import contextmanager
from pathlib import Path


def find_file_descend(filename, path):
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


def file_create(path: str | Path) -> None:
    Path(path).open("a").close()


def subprocess_run(
    cmd, *, filename: Path | None = None, check=False, **kwargs
) -> subprocess.CompletedProcess:
    if filename is None:
        return subprocess.run(cmd, **kwargs, check=check)
    else:
        with filename.open("wb") as f:
            return subprocess.run(
                cmd, check=check, stderr=subprocess.STDOUT, stdout=f, **kwargs
            )
