import pickle
import time
from dataclasses import dataclass

from hipercow.environment import environment_engine
from hipercow.root import Root
from hipercow.task import (
    TaskData,
    TaskStatus,
    TaskTimes,
    set_task_status,
    task_status,
)


@dataclass
class TaskResult:
    task_id: str
    success: bool
    data: object


def task_eval(root: Root, task_id: str, *, capture: bool = False) -> None:
    data = TaskData.read(root, task_id)
    task_eval_data(root, data, capture=capture)


def task_eval_data(root: Root, data: TaskData, *, capture: bool) -> None:
    task_id = data.task_id
    status = task_status(root, task_id)
    if not status.is_runnable():
        msg = f"Can't run '{task_id}', which has status '{status}'"
        raise Exception(msg)

    t_created = root.path_task_data(task_id).stat().st_ctime
    t_start = time.time()

    set_task_status(root, task_id, TaskStatus.RUNNING)

    assert data.method == "shell"  # noqa: S101
    res = task_eval_shell(root, data, capture=capture)

    t_end = time.time()

    status = TaskStatus.SUCCESS if res.success else TaskStatus.FAILURE
    with root.path_task_result(task_id).open("wb") as f:
        pickle.dump(res.data, f)

    times = TaskTimes(t_created, t_start, t_end)
    times.write(root, task_id)

    set_task_status(root, task_id, status)


def task_eval_shell(root: Root, data: TaskData, *, capture=False) -> TaskResult:
    cmd = data.data["cmd"]
    env = data.envvars
    path = root.path / data.path
    filename = root.path_task_log(data.task_id) if capture else None
    res = environment_engine(root, data.environment).run(
        cmd, check=False, env=env, cwd=path, filename=filename
    )
    success = res.returncode == 0
    return TaskResult(data.task_id, success, None)
