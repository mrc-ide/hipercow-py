import subprocess
import sys

import pytest
from uv import find_uv_bin

from hipercow import root
from hipercow.configure import configure
from hipercow.environment import environment_engine, environment_new
from hipercow.environment_engines import Uv
from hipercow.provision import provision, provision_history
from hipercow.task import TaskStatus, task_log, task_status
from hipercow.task_create import task_create_shell
from hipercow.task_eval import task_eval
from hipercow.util import transient_working_directory

PRINT_PYTHON = "import sys; print(sys.version_info[:2], sys.base_prefix)"


@pytest.mark.slow
def test_run_in_uv_environment_with_chosen_python(tmp_path):
    with transient_working_directory(tmp_path):
        root.init(tmp_path)
        r = root.open_root(tmp_path)

        with open("requirements.txt", "w") as f:
            f.write("cowsay\n")

        configure("example", root=r)
        # 3.13 is not a version that we test hipercow itself with, so
        # this shows that the environment's Python is independent of
        # the one running hipercow.
        environment_new("default", "uv", r, python="3.13")
        provision("default", [], root=r)
        (record,) = provision_history("default", r)
        assert record.data.cmd == ["pip", "install", "-r", "requirements.txt"]
        assert record.result is not None
        assert record.result.error is None

        tid = task_create_shell(["cowsay", "-t", "hello"], root=r)
        task_eval(tid, capture=True, root=r)
        assert task_status(tid, r) == TaskStatus.SUCCESS
        assert "| hello |" in task_log(tid, root=r)

        # The task's Python is the one uv downloaded into the
        # environment, not a system Python.
        env = environment_engine("default", r)
        assert isinstance(env, Uv)
        tid = task_create_shell(["python", "-c", PRINT_PYTHON], root=r)
        task_eval(tid, capture=True, root=r)
        assert task_status(tid, r) == TaskStatus.SUCCESS
        log = task_log(tid, root=r)
        assert log is not None
        assert "(3, 13)" in log
        assert str(env.path_uv() / "python") in log

        tid = task_create_shell(["python", "-c", "exit(3)"], root=r)
        task_eval(tid, capture=True, root=r)
        assert task_status(tid, r) == TaskStatus.FAILURE


@pytest.mark.slow
def test_run_in_uv_environment_from_lockfile(tmp_path):
    with transient_working_directory(tmp_path):
        root.init(tmp_path)
        r = root.open_root(tmp_path)

        with open("pyproject.toml", "w") as f:
            f.write(
                "[project]\n"
                'name = "example"\n'
                'version = "0.1.0"\n'
                'requires-python = ">=3.10"\n'
                'dependencies = ["cowsay"]\n'
            )
        # Lock with the running Python so that this does not download
        # one into your home directory.
        subprocess.run(
            [find_uv_bin(), "lock", "--python", sys.executable], check=True
        )
        with open(".python-version", "w") as f:
            f.write("3.12\n")

        configure("example", root=r)
        environment_new("default", "uv", r)
        provision("default", [], root=r)
        (record,) = provision_history("default", r)
        assert record.data.cmd == ["uv", "sync", "--locked"]
        assert record.result is not None
        assert record.result.error is None

        tid = task_create_shell(["cowsay", "-t", "hello"], root=r)
        task_eval(tid, capture=True, root=r)
        assert task_status(tid, r) == TaskStatus.SUCCESS

        # Python version taken from '.python-version'
        tid = task_create_shell(["python", "-c", PRINT_PYTHON], root=r)
        task_eval(tid, capture=True, root=r)
        log = task_log(tid, root=r)
        assert log is not None
        assert "(3, 12)" in log

        # uv sync uses hipercow's environment, not '.venv'
        assert not (tmp_path / ".venv").exists()
