import secrets

from hipercow.root import Root, open_root
from hipercow.task import TaskData
from hipercow.util import relative_workdir


def task_create_shell(
    cmd: list[str], envvars: dict[str, str] | None = None
) -> str:
    root = open_root()
    data = {"cmd": cmd}
    id = task_create(root, "shell", data, envvars or {})
    # task_submit_maybe(id, driver, root)
    return id


def task_create(
    root: Root, method: str, data: dict, envvars: dict[str, str]
) -> str:
    path = relative_workdir(root.path)
    task_id = new_task_id()
    TaskData(task_id, method, data, str(path), envvars).write(root)
    return task_id


def new_task_id() -> str:
    return secrets.token_hex(16)
