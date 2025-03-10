import secrets

from hipercow.driver import load_driver_optional
from hipercow.environment import environment_check
from hipercow.root import OptionalRoot, Root, open_root
from hipercow.task import TaskData, TaskStatus, set_task_status
from hipercow.util import relative_workdir


def task_create_shell(
    cmd: list[str],
    *,
    environment: str | None = None,
    envvars: dict[str, str] | None = None,
    driver: str | None = None,
    root: OptionalRoot = None,
) -> str:
    """Create a shell command task.

    This is the first type of task that we support, and more types
    will likely follow.  A shell command will evaluate an arbitrary
    command on the cluster - it does not even need to be written in
    Python! However, if you are using the `pip` environment engine
    then it will need to be `pip`-installable.

    The interface here is somewhat subject to change, but we think the
    basics here are reasonable.

    Args:
        cmd: The command to execute, as a list of strings

        environment: The name of the environment to evaluate the
            command in.  The default (`None`) will select `default` if
            available, falling back on `empty`.

        envvars: A dictionary of environment variables to set before
            the task runs.  Do not set `PATH` in here, it will not
            currently have an effect.

        driver: The driver to launch the task with.  Generally this is
            not needed as we expect most people to have a single
            driver set.

        root: The root, or if given search from the current directory.

    Returns:
        The newly-created task identifier, a 32-character hex string.
    """
    root = open_root(root)
    if not cmd:
        msg = "'cmd' cannot be empty"
        raise Exception(msg)
    data = {"cmd": cmd}
    task_id = _task_create(
        root=root,
        method="shell",
        environment=environment,
        driver=driver,
        data=data,
        envvars=envvars or {},
    )
    return task_id


def _task_create(
    *,
    root: Root,
    method: str,
    environment: str | None,
    driver: str | None,
    data: dict,
    envvars: dict[str, str],
) -> str:
    path = relative_workdir(root.path)
    task_id = _new_task_id()
    environment = environment_check(environment, root)
    TaskData(task_id, method, data, str(path), environment, envvars).write(root)
    with root.path_recent().open("a") as f:
        f.write(f"{task_id}\n")
    _submit_maybe(task_id, driver, root)
    return task_id


def _new_task_id() -> str:
    return secrets.token_hex(16)


def _submit_maybe(task_id: str, driver: str | None, root: Root) -> None:
    if dr := load_driver_optional(driver, root):
        dr.submit(task_id, root)
        set_task_status(task_id, TaskStatus.SUBMITTED, root)
