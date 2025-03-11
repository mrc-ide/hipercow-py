import secrets
import shutil
from pathlib import Path
from string import Template

from taskwait import Task, taskwait

from hipercow.dide.driver import _web_client
from hipercow.dide.mounts import Mount, detect_mounts, _backward_slash
from hipercow.dide.web import DideWebClient

BOOTSTRAP = Template(
    r"""call set_python_${version2}_64
set PIPX_HOME=\\wpia-hn\hipercow\bootstrap-py-windows\python-${version}\pipx
set PIPX_BIN_DIR=\\wpia-hn\hipercow\bootstrap-py-windows\python-${version}\bin
python \\wpia-hn\hipercow\bootstrap-py-windows\in\pipx.pyz install ${args} ${target}
"""  # noqa: E501
)


def bootstrap(
    target: str | None, *, force: bool = False, verbose: bool = False
) -> None:
    client = _web_client()
    mount = _bootstrap_mount()

    # NOTE: duplicates list in hipercow/util.py, we'll tidy this up
    # later too.
    python_versions = ["3.10", "3.11", "3.12", "3.13"]
    bootstrap_id = secrets.token_hex(4)

    target = _bootstrap_target(target, mount, bootstrap_id)
    args = _bootstrap_args(force=force, verbose=verbose)

    tasks = [
        _bootstrap_submit(client, mount, bootstrap_id, v, target, args)
        for v in python_versions
    ]
    _bootstrap_wait(tasks)


class BootstrapTask(Task):
    def __init__(
        self,
        client: DideWebClient,
        dide_id: str,
        version: str,
    ):
        self.client = client
        self.dide_id = dide_id
        self.version = version
        self.status_waiting = {"created", "submitted"}
        self.status_running = {"running"}

    def log(self) -> None:
        pass

    def status(self) -> str:
        return str(self.client.status_job(self.dide_id))

    def has_log(self) -> bool:
        return False


def _bootstrap_submit(
    client: DideWebClient,
    mount: Mount,
    bootstrap_id: str,
    version: str,
    target: str,
    args: str,
) -> BootstrapTask:
    name = f"bootstrap/{bootstrap_id}/{version}"
    path = Path("bootstrap-py-windows") / "in" / bootstrap_id / f"{version}.bat"

    path_local = mount.local / path
    path_local.parent.mkdir(parents=True, exist_ok=True)
    with path_local.open("w") as f:
        f.write(_batch_bootstrap(version, target, args))

    dide_id = client.submit(_bootstrap_unc(path), name)
    return BootstrapTask(client, dide_id, version)


def _bootstrap_target(
    target: str | None, mount: Mount, bootstrap_id: str
) -> str:
    if target is None:
        return "hipercow"
    if not Path(target).exists():
        msg = f"File '{target}' does not exist"
        raise FileNotFoundError(msg)
    dest = Path("bootstrap-py-windows") / "in" / bootstrap_id
    dest_local = mount.local / dest
    dest_local.mkdir(parents=True, exist_ok=True)
    shutil.copy(target, dest_local)
    return _bootstrap_unc(dest / Path(target).name)


def _bootstrap_args(*, force: bool, verbose: bool):
    args = ["--force" if force else "", "--verbose" if verbose else ""]
    return " ".join(args).strip()


def _bootstrap_mount(mounts: list[Mount] | None = None) -> Mount:
    for m in mounts or detect_mounts():
        if m.host == "wpia-hn.hpc" and m.remote == "hipercow":
            return m
    msg = r"Failed to find '\\wpia-hn.hpc\hipercow' in your mounts"
    raise Exception(msg)


def _bootstrap_wait(tasks: list[BootstrapTask]) -> None:
    print(f"Waiting on {len(tasks)} tasks")
    fail = 0
    for t in tasks:
        res = taskwait(t)
        print(f"  - {t.version}: {res.status}")
        if res.status != "success":
            print(f"Logs from job {t.dide_id}:")
            print(t.client.log(t.dide_id))
            fail += 1

    if fail:
        msg = f"{fail}/{len(tasks)} bootstrap tasks failed - see logs above"
        raise Exception(msg)


def _batch_bootstrap(version: str, target: str, args: str) -> str:
    data = {
        "version": version,
        "version2": version.replace(".", ""),  # Wes: update the batch filenames
        "args": args,
        "target": target,
    }
    return BOOTSTRAP.substitute(data)


def _bootstrap_unc(path: Path):
    path_str = _backward_slash(str(path))
    return f"\\\\wpia-hn\\hipercow\\{path_str}"
