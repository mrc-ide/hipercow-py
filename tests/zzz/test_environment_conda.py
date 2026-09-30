import os
import shutil

import pytest

from hipercow import root
from hipercow.configure import configure
from hipercow.environment import environment_new
from hipercow.provision import provision, provision_history
from hipercow.task import TaskStatus, task_log, task_status
from hipercow.task_create import task_create_shell
from hipercow.task_eval import task_eval
from hipercow.util import transient_working_directory

has_micromamba = bool(
    os.environ.get("HIPERCOW_MICROMAMBA") or shutil.which("micromamba")
)


@pytest.mark.slow
@pytest.mark.skipif(not has_micromamba, reason="micromamba not available")
def test_run_in_conda_environment(tmp_path, monkeypatch):
    # User configuration must not leak into the environment; if it
    # did, this unreachable channel would cause provisioning to fail.
    # micromamba only reads files with conventional names like
    # '.condarc'.
    path_condarc = tmp_path / "user" / ".condarc"
    path_condarc.parent.mkdir()
    with path_condarc.open("w") as f:
        f.write("channels:\n  - https://conda.example.invalid/nope\n")
    monkeypatch.setenv("CONDARC", str(path_condarc))

    path = tmp_path / "project"
    path.mkdir()
    with transient_working_directory(path):
        root.init(path)
        r = root.open_root(path)

        with open("environment.yml", "w") as f:
            f.write("dependencies:\n  - ripgrep\n")

        configure("example", root=r)
        environment_new("default", "conda", r)
        provision("default", [], root=r)
        (record,) = provision_history("default", r)
        assert record.data.cmd == [
            "conda",
            "install",
            "--file",
            "environment.yml",
        ]
        assert record.result is not None
        assert record.result.error is None

        tid = task_create_shell(["rg", "--version"], root=r)
        task_eval(tid, capture=True, root=r)

        assert task_status(tid, r) == TaskStatus.SUCCESS
        assert "ripgrep" in task_log(tid, root=r)

        # Failures in the task propagate through micromamba run
        tid = task_create_shell(["rg", "--no-such-option"], root=r)
        task_eval(tid, capture=True, root=r)
        assert task_status(tid, r) == TaskStatus.FAILURE
