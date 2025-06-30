import secrets
import shutil
from pathlib import Path

from taskwait import Task, taskwait

from hipercow import ui
from hipercow.dide.bootstrap_linux import bootstrap_linux_submit
from hipercow.dide.bootstrap_windows import bootstrap_windows_submit
from hipercow.dide.driver import _web_client
from hipercow.dide.mounts import Mount, _backward_slash, detect_mounts
from hipercow.dide.web import DideWebClient
from hipercow.util import read_file_if_exists


def bootstrap(
    target: str | None,
    *,
    force: bool = False,
    verbose: bool = False,
    python_versions: list[str] | None = None,
    platforms: list[str] | None = None,
) -> None:
    client = _web_client()
    mount = _bootstrap_mount()

    python_versions = _bootstrap_python_versions(python_versions)
    platforms = _bootstrap_platforms(platforms)
    bootstrap_id = secrets.token_hex(4)
    path = mount.local / _bootstrap_path(bootstrap_id)

    _bootstrap_check_pipx_pyz(path.parent)

    ui.alert_info(f"Bootstrap id: {bootstrap_id}")

    target = _bootstrap_target(target, mount, bootstrap_id)
    args = _bootstrap_args(force=force, verbose=verbose)

    tasks = [
        _bootstrap_submit(client, mount, bootstrap_id, v, p, target, args)
        for v in python_versions
        for p in platforms
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
        platform: str,
    ):
        self.client = client
        self.dide_id = dide_id
        self.version = version
        self.platform = platform
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
    platform: str,
    target: str,
    args: str,
) -> BootstrapTask:
    name = f"bootstrap/{bootstrap_id}/{version}"

    if platform == "windows":
        dide_id = bootstrap_windows_submit(
            bootstrap_id, version, mount, client, target, args, name
        )
    elif platform == "linux":
        dide_id = bootstrap_linux_submit(
            bootstrap_id, version, mount, client, target, args, name
        )

    return BootstrapTask(
        mount, bootstrap_id, client, dide_id, version, platform
    )


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
    ui.alert_info(f"Waiting on {len(tasks)} tasks")
    fail = 0
    for t in tasks:
        res = taskwait(t)
        result_str = f"{t.version}: {res.status}"
        if res.status == "success":
            ui.alert_success(result_str)
        else:
            ui.alert_danger(result_str)
        ui.logs("Logs from pipx:", read_file_if_exists(t.path_log), indent=4)
        if res.status != "success":
            ui.logs(
                f"Additional logs from cluster for task '{t.dide_id}':",
                t.client.log(t.dide_id),
                indent=4,
            )
            fail += 1

    if fail:
        msg = f"{fail}/{len(tasks)} bootstrap tasks failed - see logs above"
        raise Exception(msg)


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


def _bootstrap_platforms(platforms: list[str] | None) -> list[str]:
    if not platforms:
        platforms = ["windows", "linux"]
    return platforms
