import secrets

from hipercow.root import Root
from hipercow.task import TaskData
from hipercow.util import relative_workdir


# API here very subject to change in terms of argument order etc.
def task_create_shell(
    root: Root,
    cmd: list[str],
    *,
    envvars: dict[str, str] | None = None,
    driver: str | None = None,
) -> str:
    if not cmd:
        msg = "'cmd' cannot be empty"
        raise Exception(msg)
    data = {"cmd": cmd}
    task_id = _task_create(root, "shell", driver, data, envvars or {})
    return task_id


def _task_create(
    root: Root,
    method: str,
    driver: str | None,
    data: dict,
    envvars: dict[str, str],
) -> str:
    path = relative_workdir(root.path)
    task_id = _new_task_id()
    TaskData(task_id, method, data, str(path), envvars).write(root)
    _submit_maybe(task_id, driver, root)
    return task_id


def _new_task_id() -> str:
    return secrets.token_hex(16)


def _submit_maybe(task_id: str, driver: str | None, root: Root) -> None:
    if dr := root.load_driver(driver, allow_none=True):
        dr.submit(task_id, root)
