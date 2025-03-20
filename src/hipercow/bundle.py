"""Support for bundles of related tasks."""

import secrets

from pydantic import BaseModel

from hipercow import ui
from hipercow.root import OptionalRoot, open_root
from hipercow.task import (
    TaskStatus,
    check_task_exists,
    check_task_id,
    task_status,
)


class Bundle(BaseModel):
    """A bundle of tasks.

    Attributes:
        name: The bundle name
        task_ids: The task identifiers in the bundle
    """

    name: str
    task_ids: list[str]


def bundle_create(
    task_ids: list[str],
    name: str | None = None,
    *,
    validate: bool = True,
    overwrite: bool = True,
    root: OptionalRoot = None,
) -> str:
    """Create a new bundle from a list of tasks.

    Arguments:
        task_ids: The task identifiers in the bundle

        name: The name for the bundle.  If not given, we randomly
            create one.  The format of the name is subject to change.

        validate: Check that all tasks exist before creating the bundle.

        overwrite: Overwrite a bundle if it already exists.

        root: The root, or if not given search from the current directory.

    Returns: The name of the newly created bundle.  Also, as a side
        effect, writes out the task bundle to disk.

    """
    root = open_root(root)
    if validate:
        for i in task_ids:
            check_task_exists(i, root)
    else:
        for i in task_ids:
            check_task_id(i)
    if name is None:
        # TODO: use something better here
        name = secrets.token_hex(8)

    path = root.path_bundle(name)
    if not overwrite and path.exists():
        msg = f"Bundle '{name}' exists and overwrite is False"
        raise Exception(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    bundle = Bundle(name=name, task_ids=task_ids)
    with path.open("w") as f:
        f.write(bundle.model_dump_json())
    ui.alert_success(f"Created bundle '{name}' with {len(task_ids)} tasks")
    return name


def bundle_load(name: str, root: OptionalRoot = None) -> Bundle:
    """Load a task bundle.

    Args:
        name: The name of the bundle to load
        root: The root, or if not given search from the current directory.

    Returns:
        The loaded bundle.
    """
    root = open_root(root)
    path = root.path_bundle(name)
    if not path.exists():
        msg = f"No such bundle '{name}'"
        raise Exception(msg)
    with path.open() as f:
        json_str = f.read()
    return Bundle.model_validate_json(json_str)


def bundle_list(root: OptionalRoot = None) -> list[str]:
    """List bundles.

    Args:
        root: The root, or if not given search from the current directory.

    Returns: The names of known bundles.  Currently the order of these
        is arbitrary.

    """
    root = open_root(root)
    path = root.path_bundle(None)
    # We could/should order by time here; we do a similar thing with
    # recent tasks.  Alternatively we might want a verbose mode that
    # stores this?  Or we could store time within the bundle, that
    # might make more sense but requiring serialising out as json,
    # possibly with pydantic?  Certainly this metadata would make
    # bundles more useful.
    nms = [x.name for x in path.glob("*")]
    return nms


def bundle_delete(name: str, root: OptionalRoot = None) -> None:
    """Delete a bundle.

    Note that this does not delete the tasks in the bundle, just the
    bundle itself.

    Args:
        name: The name of the bundle to delete
        root: The root, or if not given search from the current directory.

    Returns:
        Nothing, called for side effects only.

    """
    root = open_root(root)
    path = root.path_bundle(name)
    if not path.exists():
        msg = f"Can't delete bundle '{name}', it does not exist"
        raise Exception(msg)

    path.unlink()
    ui.alert_success("Deleted bundle '{name}'")


def bundle_status(name: str, root: OptionalRoot = None) -> list[TaskStatus]:
    """Get the statuses of tasks in a bundle.

    Depending on the context, `bundle_status_reduce()` may be more
    appropriate function to use, which attempts to reduce the list of
    statuses into the single "worst" status.

    Args:
        name: The name of the bundle to get the statuses for.
        root: The root, or if not given search from the current directory.

    Returns:
        A list of statuses, one per task.  These are stored in
        the same order as the original bundle.

    """
    bundle = bundle_load(name, root=root)
    return [task_status(i, root=root) for i in bundle.task_ids]


def bundle_status_reduce(name: str, root: OptionalRoot = None) -> TaskStatus:
    """Get the overall status from a bundle.

    Args:
        name: The name of the bundle to get the statuses for.
        root: The root, or if not given search from the current directory.

    Returns:
        The overall bundle status.
    """
    return _status_reduce(bundle_status(name, root))


def _status_reduce(status: list[TaskStatus]) -> TaskStatus:
    order = [
        TaskStatus.CREATED,
        TaskStatus.FAILURE,
        TaskStatus.CANCELLED,
        TaskStatus.RUNNING,
        TaskStatus.SUBMITTED,
        TaskStatus.SUCCESS,
    ]
    return order[min(order.index(i) for i in status)]


# Not implemented - result, cancel, wait, logs, retry
