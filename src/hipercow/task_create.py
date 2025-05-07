import secrets

from hipercow.driver import load_driver_optional
from hipercow.environment import environment_check
from hipercow.resources import TaskResources
from hipercow.root import OptionalRoot, Root, open_root
from hipercow.task import TaskData, TaskStatus, set_task_status, task_data_write
from hipercow.util import relative_workdir


def task_create_shell(
    cmd: list[str],
    *,
    environment: str | None = None,
    envvars: dict[str, str] | None = None,
    resources: TaskResources | None = None,
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

        resources: Optional resources required by your task.

        driver: The driver to launch the task with.  Generally this is
            not needed as we expect most people to have a single
            driver set.

        root: The root, or if not given search from the current directory.

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
        resources=resources,
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
    resources: TaskResources | None,
    envvars: dict[str, str],
) -> str:
    path = relative_workdir(root.path)
    task_id = _new_task_id()
    environment = environment_check(environment, root)
    dr = load_driver_optional(driver, root)
    if resources:
        if not dr:
            msg = "Can't specify resources, as driver is not given"
            raise Exception(msg)
        resources = dr.resources().validate_resources(resources)
    task_data = TaskData(
        task_id=task_id,
        method=method,
        data=data,
        path=str(path),
        environment=environment,
        resources=resources,
        envvars=envvars,
    )
    task_data_write(task_data, root)
    with root.path_recent().open("a") as f:
        f.write(f"{task_id}\n")
    if dr:
        dr.submit(task_id, resources, root)
        set_task_status(task_id, TaskStatus.SUBMITTED, dr.name, root)
    return task_id


def _new_task_id() -> str:
    return secrets.token_hex(16)
