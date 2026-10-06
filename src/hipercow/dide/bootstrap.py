"""Install hipercow onto the hipercow share, for jobs to run.

For each platform and python version we submit a cluster job that
runs `bootstrap_install.py` (see there for the details) using a copy
of uv kept on the share, so the nodes do not need python installed.
"""

import datetime
import secrets
import shutil
from pathlib import Path
from string import Template

from taskwait import Task, taskwait

from hipercow import ui
from hipercow.dide import bootstrap_install
from hipercow.dide.batch_linux import BOOTSTRAP_ROOT_LINUX
from hipercow.dide.bootstrap_uv import (
    bootstrap_uv,
    bootstrap_uv_path,
    uv_version,
)
from hipercow.dide.driver import _web_client
from hipercow.dide.mounts import (
    Mount,
    _backward_slash,
    _forward_slash,
    detect_mounts,
)
from hipercow.dide.web import DideWebClient
from hipercow.resources import TaskResources
from hipercow.util import PYTHON_VERSIONS, read_file_if_exists

BOOTSTRAP_PLATFORMS = ["windows", "linux"]

# The bootstrap, as seen by the jobs that install into it.  Windows
# jobs use the share directly, rather than mapping it to I: as the
# jobs that run tasks do.
BOOTSTRAP_ROOT = {
    "linux": BOOTSTRAP_ROOT_LINUX,
    "windows": r"\\wpia-hn-app\hipercow\bootstrap-py-windows",
}

BOOTSTRAP_SH = Template(r"""#!/bin/bash
echo working directory: $$(pwd)

source /etc/profile

# No python is needed on the node: uv downloads it into a temporary
# directory here and bootstrap_install.py copies it onto the share.
export UV_PYTHON_INSTALL_DIR=$$(mktemp -d)
export UV_MANAGED_PYTHON=1
export UV_NO_CACHE=1
export UV_NO_CONFIG=1
export PYTHONUNBUFFERED=1

echo Installing hipercow for python ${version} using ${uv}
${uv} run --no-project --python ${version} ${path_in}/bootstrap_install.py --root ${root} --python-version ${version} --name ${name} --uv ${uv} ${args} ${target} > ${path_in}/${version}.log 2>&1

ErrorCode=$$?

rm -rf $$UV_PYTHON_INSTALL_DIR

echo ERRORLEVEL was $$ErrorCode
if [ $$ErrorCode -eq 0 ]; then
  echo Installation appears to have been successful
else
  echo Installation failed
  exit $$ErrorCode
fi
""")  # noqa: E501

BOOTSTRAP_BAT = Template(r"""@ECHO on
ECHO working directory: %CD%

REM No python is needed on the node: uv downloads it into a temporary
REM directory here and bootstrap_install.py copies it onto the share.
set UV_PYTHON_INSTALL_DIR=%TEMP%\hipercow-bootstrap-${bootstrap_id}-${version}
set UV_MANAGED_PYTHON=1
set UV_NO_CACHE=1
set UV_NO_CONFIG=1
set PYTHONUNBUFFERED=1

ECHO Installing hipercow for python ${version} using ${uv}
${uv} run --no-project --python ${version} ${path_in}\bootstrap_install.py --root ${root} --python-version ${version} --name ${name} --uv ${uv} ${args} ${target} > ${path_in}\${version}.log 2>&1
set ErrorCode=%ERRORLEVEL%
rmdir /s /q "%UV_PYTHON_INSTALL_DIR%"
@ECHO ERRORLEVEL was %ErrorCode%
if %ErrorCode% == 0 (
  @ECHO Installation appears to have been successful
) else (
  @ECHO Installation failed
  EXIT /b %ErrorCode%
)
""")  # noqa: E501


def bootstrap(
    target: str | None,
    *,
    verbose: bool = False,
    python_versions: list[str] | None = None,
    platforms: list[str] | None = None,
) -> None:
    if target is not None and not Path(target).exists():
        msg = f"File '{target}' does not exist"
        raise FileNotFoundError(msg)

    client = _web_client()
    mount = _bootstrap_mount()

    python_versions = python_versions or PYTHON_VERSIONS
    platforms = _bootstrap_platforms(platforms)
    bootstrap_id = secrets.token_hex(4)
    name = _bootstrap_install_name(bootstrap_id)
    uv = uv_version()

    ui.alert_info(f"Bootstrap id: {bootstrap_id}")
    ui.alert_info(f"Installing as '{name}', using uv {uv}")

    args = "--verbose" if verbose else ""
    tasks = []
    for p in platforms:
        bootstrap_uv(mount, p, uv)
        target_p = _bootstrap_prepare(mount, bootstrap_id, p, target)
        tasks += [
            _bootstrap_submit(client, mount, bootstrap_id, name, v, p, target_p, args, uv) for v in python_versions
        ]
    # The scripts and logs in 'bootstrap-py-<platform>/in/<id>' are
    # left on the share, in case they are needed for debugging.
    _bootstrap_wait(tasks)


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
        self.path_log = mount.local / _bootstrap_path(bootstrap_id, platform) / f"{version}.log"

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
    name: str,
    version: str,
    platform: str,
    target: str | None,
    args: str,
    uv_version: str,
) -> BootstrapTask:
    if platform not in BOOTSTRAP_PLATFORMS:
        msg = f"Unsupported platform '{platform}'"
        raise ValueError(msg)

    script = _bootstrap_script(platform, bootstrap_id, name, version, target, args, uv_version)
    if platform == "windows":
        path = _bootstrap_path(bootstrap_id, platform) / f"{version}.bat"
        newline = None
        submit_path = f"\\\\wpia-hn\\hipercow\\{_backward_slash(str(path))}"
        queue = "AllNodes"  # not BuildQueue, for now
    else:
        path = _bootstrap_path(bootstrap_id, platform) / f"{version}.sh"
        newline = "\n"
        submit_path = f"/mnt/cluster/Hipercow/{_forward_slash(str(path))}"
        queue = "LinuxNodes"

    path_local = mount.local / path
    path_local.parent.mkdir(parents=True, exist_ok=True)
    with path_local.open("w", newline=newline) as f:
        f.write(script)

    job_name = f"bootstrap/{bootstrap_id}/{platform}/{version}"
    resources = TaskResources(queue=queue)
    dide_id = client.submit(submit_path, job_name, resources)
    return BootstrapTask(mount, bootstrap_id, client, dide_id, version, platform)


def _bootstrap_script(
    platform: str,
    bootstrap_id: str,
    name: str,
    version: str,
    target: str | None,
    args: str,
    uv_version: str,
    root: str | None = None,
) -> str:
    root = root or BOOTSTRAP_ROOT[platform]
    sep = "\\" if platform == "windows" else "/"
    path_in = sep.join([root, "in", bootstrap_id])
    uv = sep.join([root, *bootstrap_uv_path(platform, uv_version).split("/")])
    data = {
        "root": root,
        "uv": uv,
        "bootstrap_id": bootstrap_id,
        "path_in": path_in,
        "name": name,
        "version": version,
        "args": args,
        "target": "hipercow" if target is None else f"{path_in}{sep}{target}",
    }
    template = BOOTSTRAP_BAT if platform == "windows" else BOOTSTRAP_SH
    return template.substitute(data)


# Copy everything that the installation needs onto the share.  If a
# local file is given as the target, it is copied alongside the
# installer and we return its file name, which the batch file turns
# into a full path on the node.
def _bootstrap_prepare(mount: Mount, bootstrap_id: str, platform: str, target: str | None) -> str | None:
    dest = mount.local / _bootstrap_path(bootstrap_id, platform)
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(bootstrap_install.__file__, dest / "bootstrap_install.py")
    if target is None:
        return None
    shutil.copy(target, dest)
    return Path(target).name


def _bootstrap_install_name(bootstrap_id: str) -> str:
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return f"{now:%Y%m%d%H%M%S}-{bootstrap_id}"


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
        result_str = f"{t.platform} {t.version}: {res.status}"
        if res.status == "success":
            ui.alert_success(result_str)
        else:
            ui.alert_danger(result_str)
        ui.logs("Logs from bootstrap:", read_file_if_exists(t.path_log), indent=4)
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


def _bootstrap_path(bootstrap_id: str, platform: str) -> Path:
    return Path(f"bootstrap-py-{platform}") / "in" / bootstrap_id


def _bootstrap_platforms(platforms: list[str] | None) -> list[str]:
    if not platforms:
        return BOOTSTRAP_PLATFORMS
    for p in platforms:
        if p not in BOOTSTRAP_PLATFORMS:
            valid = ", ".join(BOOTSTRAP_PLATFORMS)
            msg = f"Unsupported platform '{p}'; must be one of {valid}"
            raise ValueError(msg)
    return platforms
