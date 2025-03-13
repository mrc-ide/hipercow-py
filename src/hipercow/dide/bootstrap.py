import secrets
import shutil
from pathlib import Path
from string import Template

from taskwait import Task, taskwait

from hipercow.dide.driver import _web_client
from hipercow.dide.mounts import Mount, _backward_slash, detect_mounts
from hipercow.dide.web import DideWebClient
from hipercow.resources import TaskResources
from hipercow.util import read_file_if_exists

BOOTSTRAP = Template(
    r"""@ECHO on
ECHO working directory: %CD%
call set_python_${version2}_64
set PIPX_HOME=\\wpia-hn-app\hipercow\bootstrap-py-windows\python-${version}\pipx
set PIPX_BIN_DIR=\\wpia-hn-app\hipercow\bootstrap-py-windows\python-${version}\bin

echo "Running pipx to install hipercow"
python \\wpia-hn-app\hipercow\bootstrap-py-windows\in\pipx.pyz install ${args} ${target} > \\wpia-hn-app\hipercow\bootstrap-py-windows\in\${bootstrap_id}\${version}.log 2>&1
set ErrorCode=%ERRORLEVEL%
@ECHO ERRORLEVEL was %ErrorCode%
if %ErrorCode% == 0 (
  @ECHO Installation appears to have been successful
) else (
  @ECHO Installation failed
  EXIT /b %ErrorCode%
)
"""  # noqa: E501
)


def bootstrap(
    target: str | None,
    *,
    force: bool = False,
    verbose: bool = False,
    python_versions: list[str] | None = None,
) -> None:
    client = _web_client()
    mount = _bootstrap_mount()

    python_versions = _bootstrap_python_versions(python_versions)
    bootstrap_id = secrets.token_hex(4)
    path = mount.local / _bootstrap_path(bootstrap_id)

    _bootstrap_check_pipx_pyz(path.parent)

    print(f"Bootstrap id: {bootstrap_id}")

    target = _bootstrap_target(target, mount, bootstrap_id)
    args = _bootstrap_args(force=force, verbose=verbose)

    tasks = [
        _bootstrap_submit(client, mount, bootstrap_id, v, target, args)
        for v in python_versions
    ]
    _bootstrap_wait(tasks)
    # We could clean up here with 'shutil.rmtree(path)' but wait until
    # things setle down first, as this removes any hope of debugging,
    # really.


class BootstrapTask(Task):
    def __init__(
        self,
        mount: Mount,
        bootstrap_id: str,
        client: DideWebClient,
        dide_id: str,
        version: str,
    ):
        self.client = client
        self.dide_id = dide_id
        self.version = version
        self.status_waiting = {"created", "submitted"}
        self.status_running = {"running"}
        self.path_log = Path(
            mount.local / _bootstrap_path(bootstrap_id) / f"{version}.log"
        )

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
    path = _bootstrap_path(bootstrap_id) / f"{version}.bat"

    path_local = mount.local / path
    path_local.parent.mkdir(parents=True, exist_ok=True)
    with path_local.open("w") as f:
        f.write(_batch_bootstrap(bootstrap_id, version, target, args))

    resources = TaskResources(queue="AllNodes")  # not BuildQueue, for now
    dide_id = client.submit(_bootstrap_unc(path), name, resources)
    return BootstrapTask(mount, bootstrap_id, client, dide_id, version)


def _bootstrap_target(
    target: str | None, mount: Mount, bootstrap_id: str
) -> str:
    if target is None:
        return "hipercow"
    if not Path(target).exists():
        msg = f"File '{target}' does not exist"
        raise FileNotFoundError(msg)
    dest = _bootstrap_path(bootstrap_id)
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

        print("Logs from pipx:")
        print(read_file_if_exists(t.path_log))

        if res.status != "success":
            print(f"Additional logs from cluster for task '{t.dide_id}':")
            print(t.client.log(t.dide_id))
            fail += 1

    if fail:
        msg = f"{fail}/{len(tasks)} bootstrap tasks failed - see logs above"
        raise Exception(msg)


def _batch_bootstrap(
    bootstrap_id: str, version: str, target: str, args: str
) -> str:
    data = {
        "bootstrap_id": bootstrap_id,
        "version": version,
        "version2": version.replace(".", ""),  # Wes: update the batch filenames
        "args": args,
        "target": target,
    }
    return BOOTSTRAP.substitute(data)


def _bootstrap_unc(path: Path):
    path_str = _backward_slash(str(path))
    return f"\\\\wpia-hn\\hipercow\\{path_str}"


def _bootstrap_path(bootstrap_id: str) -> Path:
    return Path("bootstrap-py-windows") / "in" / bootstrap_id


def _bootstrap_check_pipx_pyz(path: Path) -> None:
    if not (path / "pipx.pyz").exists():
        url = "https://github.com/pypa/pipx/releases"
        msg = (
            f"Expected 'pipx.pyz' to be found at '{path}'; download from {url}"
        )
        raise Exception(msg)


def _bootstrap_python_versions(versions: list[str] | None) -> list[str]:
    if not versions:
        # NOTE: duplicates list in hipercow/util.py, we'll tidy this up
        # later too.
        versions = ["3.10", "3.11", "3.12", "3.13"]
    return versions
