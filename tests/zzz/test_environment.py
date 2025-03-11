import pytest

from hipercow import root
from hipercow.configure import configure
from hipercow.environment import environment_new
from hipercow.provision import provision
from hipercow.task import TaskStatus, task_log, task_status
from hipercow.task_create import task_create_shell
from hipercow.task_eval import task_eval
from hipercow.util import transient_working_directory


@pytest.mark.slow
def test_run_in_environment(tmp_path):
    with transient_working_directory(tmp_path):
        root.init(tmp_path)
        r = root.open_root(tmp_path)

        with open("requirements.txt", "w") as f:
            f.write("cowsay\n")

        configure("example", root=r)
        environment_new("default", "pip", r)
        provision("default", [], root=r)
        tid = task_create_shell(["cowsay", "-t", "hello"], root=r)
        task_eval(tid, capture=True, root=r)

        assert task_status(tid, r) == TaskStatus.SUCCESS
        assert "| hello |" in task_log(tid, root=r)
