"""Run the real bootstrap, and then real jobs, against a fake share.

These run the batch files that 'hipercow dide bootstrap' and the dide
driver write, as a cluster node would, but with the hipercow share
replaced by a temporary directory.  The bootstrap downloads the real
uv release for the platform and installs hipercow from a wheel built
from this source tree.  On Linux the jobs run with a PATH that has no
python on it, to show that the nodes do not need one.
"""

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from uv import find_uv_bin

from hipercow import root
from hipercow.__about__ import __version__
from hipercow.configure import configure
from hipercow.dide.batch_linux import PROVISION_SH, TASK_RUN_SH
from hipercow.dide.bootstrap import (
    _bootstrap_install_name,
    _bootstrap_prepare,
    _bootstrap_script,
)
from hipercow.dide.bootstrap_install import (
    METADATA,
    python_path,
    read_current,
    scripts_path,
)
from hipercow.dide.bootstrap_uv import bootstrap_uv, uv_version
from hipercow.dide.mounts import Mount
from hipercow.environment import environment_new
from hipercow.provision import ProvisioningData, provision_history
from hipercow.task import TaskStatus, task_log, task_status
from hipercow.task_create import task_create_shell
from hipercow.util import transient_working_directory

# Not a version that we run the tests with, so the installation can't
# be using the python that runs the tests.
PYTHON_VERSION = "3.13"
BOOTSTRAP_ID = "0123abcd"

is_linux = sys.platform == "linux" and platform.machine() == "x86_64"
is_windows = sys.platform == "win32"


def _build_wheel(path: Path) -> Path:
    src = Path(__file__).parents[2]
    cmd = [find_uv_bin(), "build", "--wheel", "--python", sys.executable]
    subprocess.run([*cmd, "--out-dir", str(path), str(src)], check=True)
    (wheel,) = path.glob("hipercow-*.whl")
    return wheel


def _bootstrap(tmp_path: Path, platform: str) -> tuple[Path, str]:
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)
    bootstrap_root = tmp_path / f"bootstrap-py-{platform}"
    uv = uv_version()
    bootstrap_uv(mount, platform, uv)
    wheel = _build_wheel(tmp_path / "dist")
    name = _bootstrap_install_name(BOOTSTRAP_ID)
    target = _bootstrap_prepare(mount, BOOTSTRAP_ID, platform, str(wheel))
    path_in = bootstrap_root / "in" / BOOTSTRAP_ID
    script = _bootstrap_script(
        platform,
        BOOTSTRAP_ID,
        name,
        PYTHON_VERSION,
        target,
        "",
        uv,
        str(bootstrap_root),
    )
    if platform == "linux":
        path_script = path_in / f"{PYTHON_VERSION}.sh"
        cmd = ["bash", str(path_script)]
    else:
        path_script = path_in / f"{PYTHON_VERSION}.bat"
        cmd = ["cmd", "/c", str(path_script)]
    with path_script.open("w", newline="\n" if platform == "linux" else None) as f:
        f.write(script)
    env = _node_env(tmp_path) if platform == "linux" else None
    res = subprocess.run(cmd, env=env, check=False)
    log = path_in / f"{PYTHON_VERSION}.log"
    assert res.returncode == 0, log.read_text()
    return bootstrap_root / f"python-{PYTHON_VERSION}", name


def _check_installation(base: Path, name: str) -> Path:
    assert read_current(base) == name
    dest = base / "installs" / name
    with (dest / METADATA).open() as f:
        metadata = json.load(f)
    assert metadata["hipercow"] == __version__
    assert metadata["python"].startswith(f"{PYTHON_VERSION}.")
    assert metadata["python_executable"] == str(python_path(dest))
    assert metadata["uv"].startswith(f"uv {uv_version()}")
    # The installation contains its own python, with hipercow and uv
    res = subprocess.run(
        [str(scripts_path(dest, "hipercow")), "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert __version__ in res.stdout
    assert scripts_path(dest, "uv").exists()
    return dest


# A PATH containing just the programs that the batch files use, and
# no python.
def _node_env(tmp_path: Path) -> dict[str, str]:
    path_bin = tmp_path / "node-bin"
    if not path_bin.exists():
        path_bin.mkdir()
        tools = ["bash", "sh", "cat", "echo", "hostname", "mktemp", "rm"]
        tools += ["id", "ls", "sed", "grep", "tr", "uname", "date", "mkdir"]
        for tool in tools:
            found = shutil.which(tool)
            if found:
                (path_bin / tool).symlink_to(found)
    assert shutil.which("python3", path=str(path_bin)) is None
    assert shutil.which("python", path=str(path_bin)) is None
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return {"PATH": str(path_bin), "HOME": str(home), "CCP_NUMCPUS": "1"}


def _run_job(template, data: dict[str, str], path: Path, env: dict[str, str]):
    with path.open("w", newline="\n") as f:
        f.write(template.substitute(data))
    return subprocess.run(["bash", str(path)], env=env, check=False)


@pytest.mark.slow
@pytest.mark.skipif(not is_linux, reason="needs linux x86_64")
def test_bootstrap_and_jobs_on_linux_without_python(tmp_path):
    base, name = _bootstrap(tmp_path, "linux")
    dest = _check_installation(base, name)
    # The installation's python is a copy, not a link to the one uv
    # downloaded into a temporary directory on the node.
    assert python_path(dest).resolve().is_relative_to(dest)
    env = _node_env(tmp_path)
    assert not any(Path(env["HOME"]).iterdir())

    # Now run jobs as the dide driver would, using that installation
    project = tmp_path / "project"
    root.init(project)
    r = root.open_root(project)
    core = {
        "hostname": "test",
        "date": "today",
        "python_version": PYTHON_VERSION,
        "hipercow_version": __version__,
        "hipercow_root_path": str(project),
        "bootstrap_root": str(base.parent),
    }
    with transient_working_directory(project):
        configure("example", root=r)
        environment_new("default", "uv", r, python="3.12")

        # Provisioning creates the environment using uv from the
        # installation, which downloads python 3.12 for it.
        data = ProvisioningData(name="default", id="abc123", cmd=["pip", "install", "cowsay"])
        path = r.path_provision_data("default", data.id)
        path.parent.mkdir(parents=True)
        path.write_text(data.model_dump_json())
        res = _run_job(
            PROVISION_SH,
            core | {"environment_name": "default", "provision_id": data.id},
            path.parent / "run.sh",
            env,
        )
        assert res.returncode == 0, r.path_provision_log("default", data.id)
        (record,) = provision_history("default", r)
        assert record.result is not None
        assert record.result.error is None

        code = "import sys; print(sys.version_info[:2], sys.base_prefix)"
        for cmd, expected in [
            (["cowsay", "-t", "moo"], "| moo |"),
            (["python", "-c", code], "(3, 12)"),
        ]:
            tid = task_create_shell(cmd, root=r)
            res = _run_job(
                TASK_RUN_SH,
                core | {"task_id": tid, "task_id_1": tid[:2], "task_id_2": tid[2:]},
                r.path_task(tid) / "task_run.sh",
                env,
            )
            log = task_log(tid, root=r)
            assert res.returncode == 0, log
            assert task_status(tid, r) == TaskStatus.SUCCESS
            assert log is not None
            assert expected in log

    # Nothing was written to the home directory
    assert not any(Path(env["HOME"]).iterdir())


@pytest.mark.slow
@pytest.mark.skipif(not is_windows, reason="needs windows")
def test_bootstrap_on_windows(tmp_path):
    base, name = _bootstrap(tmp_path, "windows")
    dest = _check_installation(base, name)
    assert python_path(dest).exists()
