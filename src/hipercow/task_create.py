import secrets

from hipercow.driver import load_driver_optional
from hipercow.environment import environment_check
from hipercow.root import Root
from hipercow.task import TaskData, TaskStatus, set_task_status
from hipercow.util import relative_workdir


# API here very subject to change in terms of argument order etc.
def task_create_shell(
    root: Root,
    cmd: list[str],
    *,
    environment: str | None = None,
    envvars: dict[str, str] | None = None,
    driver: str | None = None,
) -> str:
    if not cmd:
        msg = "'cmd' cannot be empty"
        raise Exception(msg)
    data = {"cmd": cmd}
    task_id = _task_create(
        root,
        method="shell",
        environment=environment,
        driver=driver,
        data=data,
        envvars=envvars or {},
    )
    return task_id


def _task_create(
    root: Root,
    *,
    method: str,
    environment: str | None,
    driver: str | None,
    data: dict,
    envvars: dict[str, str],
) -> str:
    path = relative_workdir(root.path)
    task_id = _new_task_id()
    environment = environment_check(root, environment)
    TaskData(task_id, method, data, str(path), environment, envvars).write(root)
    _submit_maybe(task_id, driver, root)
    return task_id


def _new_task_id() -> str:
    return secrets.token_hex(16)


def _submit_maybe(task_id: str, driver: str | None, root: Root) -> None:
    if dr := load_driver_optional(root, driver):
        dr.submit(task_id, root)
        set_task_status(root, task_id, TaskStatus.SUBMITTED)
