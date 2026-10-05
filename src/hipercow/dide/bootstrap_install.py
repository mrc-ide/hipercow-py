"""Install hipercow into the bootstrap area on the hipercow share.

This script is copied onto the share by `hipercow dide bootstrap` and
run by a cluster job with `uv run --python <version>`, so it must use
only the standard library and must not import hipercow.  The nodes do
not need python installed: uv downloads it into a temporary directory
on the node before running this script.

Every run creates a brand new, self-contained installation at

    <root>/python-<version>/installs/<name>

by copying the python that is running this script there and then
installing hipercow into it with uv.  We copy rather than let uv
install python onto the share directly because uv links each python
minor version to its latest patch version, and on Windows that link
is a junction, which cannot be created on a network share.  The copy
is an ordinary directory, with no links outside itself, so it works
on both platforms and is removed along with the installation.

Only once the installation has passed a smoke test do we point
`<root>/python-<version>/current` at it; the batch files that run
tasks read that file to find hipercow.  We never modify an
installation in place because running jobs hold files open within it
(on Windows these cannot be replaced at all, which is why upgrading
with `pipx` failed).  Old installations are removed once they have
been out of use for long enough that no job should still be using
them.
"""

import argparse
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
import time
from pathlib import Path

CURRENT = "current"
INSTALLS = "installs"
METADATA = "hipercow-bootstrap.json"

# Remove an installation once it has been superseded for this long
PRUNE_AFTER = datetime.timedelta(days=30)
# Remove an installation that never completed after this long
PRUNE_INCOMPLETE_AFTER = datetime.timedelta(days=1)

RE_NAME = re.compile(r"^([0-9]{14})-[0-9a-f]+$")


class BootstrapError(Exception):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--uv", required=True)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("target")
    args = parser.parse_args(argv)

    found = "{}.{}".format(*sys.version_info[:2])
    if found != args.python_version:
        print(
            f"Expected python {args.python_version} but found {found} "
            f"at '{sys.executable}'"
        )
        return 1

    if not RE_NAME.match(args.name):
        print(f"Invalid installation name '{args.name}'")
        return 1

    base = Path(args.root) / f"python-{args.python_version}"
    dest = base / INSTALLS / args.name
    if dest.exists():
        print(f"Installation '{dest}' already exists")
        return 1

    dest.parent.mkdir(parents=True, exist_ok=True)
    previous = read_current(base)
    if previous:
        print(f"Current installation is '{previous}'")
    else:
        print("There is no current installation")
    print(f"Installing '{args.target}' into '{dest}'")
    try:
        version = install(dest, args.target, args.uv, verbose=args.verbose)
        set_current(base, args.name)
    except (BootstrapError, OSError) as e:
        print(f"Installation failed: {e}")
        if read_current(base) != args.name:
            shutil.rmtree(dest, ignore_errors=True)
        return 1

    print(f"hipercow {version} is now current for python {args.python_version}")

    try:
        prune(base / INSTALLS, args.name, _now())
    except OSError as e:
        print(f"Failed to remove old installations: {e}")

    return 0


def install(dest: Path, target: str, uv: str, *, verbose: bool) -> str:
    copy_python(Path(sys.base_prefix), dest)

    python = str(python_path(dest))
    uv_pip = [uv, "pip"]
    _run(
        [
            *uv_pip,
            "install",
            "--python",
            python,
            *(["--verbose"] if verbose else []),
            target,
        ]
    )

    # Check the installation actually works before any job can see it.
    _run([str(scripts_path(dest, "hipercow")), "--help"], capture=True)
    code = "from importlib.metadata import version; print(version('hipercow'))"
    version = _run([python, "-c", code], capture=True).strip()
    packages = _run(
        [*uv_pip, "freeze", "--python", python], capture=True
    ).splitlines()
    print("Installed packages:")
    for p in packages:
        print(f"    {p}")

    metadata = {
        "name": dest.name,
        "hipercow": version,
        "target": target,
        "python": sys.version,
        "python_executable": python,
        "uv": _run([uv, "--version"], capture=True).strip(),
        "host": platform.node(),
        "created": _now().isoformat(),
        "packages": packages,
    }
    with (dest / METADATA).open("w") as f:
        json.dump(metadata, f, indent=2)
    return version


def copy_python(home: Path, dest: Path) -> None:
    # 'home' is uv's installation of python, which is a standalone
    # build that still works after being moved.  Keep symlinks as
    # they are because they are all relative, within the installation
    # (and on Windows there are none).
    home = home.resolve()
    print(f"Copying python from '{home}'")
    shutil.copytree(home, dest, symlinks=True)
    # uv marks the pythons that it manages so that nothing else
    # installs packages into them; this copy is ours to install into.
    stdlib = sysconfig.get_path("stdlib", vars={"installed_base": str(dest)})
    (Path(stdlib) / "EXTERNALLY-MANAGED").unlink(missing_ok=True)


def python_path(path: Path) -> Path:
    if sys.platform == "win32":
        return path / "python.exe"
    return path / "bin" / "python3"


def scripts_path(path: Path, name: str) -> Path:
    if sys.platform == "win32":
        return path / "Scripts" / f"{name}.exe"
    return path / "bin" / name


def read_current(base: Path) -> str | None:
    try:
        return (base / CURRENT).read_text().strip()
    except FileNotFoundError:
        return None


def set_current(base: Path, name: str, *, attempts: int = 10) -> None:
    # Write a new file and rename it over the old one, so that a job
    # starting up sees either the old or new value and never a partly
    # written file.  No trailing newline as Windows reads this with
    # 'set /p'.  On Windows the rename fails while a job has the file
    # open, which is only ever for an instant, so retry a few times.
    tmp = base / f"{CURRENT}.{name}"
    tmp.write_text(name)
    try:
        for i in range(attempts):
            try:
                os.replace(tmp, base / CURRENT)
                return
            except PermissionError:
                if i == attempts - 1:
                    raise
                time.sleep(1)
    finally:
        tmp.unlink(missing_ok=True)


def prune(installs: Path, current: str, now: datetime.datetime) -> None:
    for p in installs.glob("*.trash"):
        shutil.rmtree(p, ignore_errors=True)
    found = sorted(
        p.name
        for p in installs.iterdir()
        if p.is_dir() and RE_NAME.match(p.name)
    )
    complete = [x for x in found if (installs / x / METADATA).exists()]
    for x in found:
        if x == current:
            continue
        if x in complete:
            # An installation stopped being used when the next one was
            # created, give or take the time taken to install it.
            newer = [y for y in complete if y > x]
            if not newer or now - _created(newer[0]) < PRUNE_AFTER:
                continue
        elif now - _created(x) < PRUNE_INCOMPLETE_AFTER:
            continue
        _remove(installs / x)


def _remove(path: Path) -> None:
    # Move out of the way first so that a job never finds a partly
    # deleted installation; on Windows this also fails if anything
    # within the installation is still in use.
    trash = path.with_name(f"{path.name}.trash")
    try:
        path.rename(trash)
    except OSError as e:
        print(f"Not removing '{path.name}', which may still be in use: {e}")
        return
    shutil.rmtree(trash, ignore_errors=True)
    print(f"Removed old installation '{path.name}'")


def _created(name: str) -> datetime.datetime:
    m = RE_NAME.match(name)
    if not m:
        msg = f"Invalid installation name '{name}'"
        raise ValueError(msg)
    return datetime.datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(
        tzinfo=datetime.timezone.utc
    )


def _now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


def _run(cmd: list[str], *, capture: bool = False) -> str:
    print(f"> {' '.join(cmd)}")
    res = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        text=True,
        errors="replace",
    )
    if res.returncode != 0:
        if capture:
            print(res.stdout)
        msg = f"Command failed with exit code {res.returncode}"
        raise BootstrapError(msg)
    return res.stdout or ""


if __name__ == "__main__":
    sys.exit(main())
