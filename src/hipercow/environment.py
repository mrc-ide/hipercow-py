import pickle
import shutil
from dataclasses import dataclass

from hipercow.environment_engines import (
    Empty,
    EnvironmentEngine,
    Pip,
)
from hipercow.root import OptionalRoot, Root, open_root


@dataclass
class EnvironmentConfiguration:
    engine: str

    # As with elsewhere, we will need to avoid actually serialising
    # the instance itself and only the configuration. Ignore this for
    # now, even though this will create versioning headaches for us.
    def write(self, name: str, root: Root):
        path = root.path_environment_config(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def read(name: str, root: Root) -> "EnvironmentConfiguration":
        with root.path_environment_config(name).open("rb") as f:
            return pickle.load(f)


# Called 'new' and not 'create' to make it clear that this does not
# actually create the environment, just the definition of that
# environment.
def environment_new(name: str, engine: str, root: OptionalRoot = None) -> None:
    """Create a new environment.

    Creating an environment selects a name and declares the engine for
    the environment.  After doing this, you will certainly want to
    provision the environment using `provision()`.

    Args:
        name: The name for the environment.  The name `default` is a
            good choice if you only want a single environment, as this
            is the environment used by default.  You cannot use
            `empty` as that is a special empty environment.

        engine: The environment engine to use.  The options here are
            `pip` and `empty`.  Soon we will support `conda` too.

        root: The root, or if not given search from the current directory.

    Returns:
        Nothing, called for side effects.

    """
    root = open_root(root)
    path = root.path_environment(name)

    # We might make this friendlier later
    if name == "empty" or path.exists():
        msg = f"Environment '{name}' already exists"
        raise Exception(msg)

    if engine not in {"pip", "empty"}:
        msg = "Only the 'pip' and 'empty' engines are supported"
        raise Exception(msg)

    print(f"Creating environment '{name}' using '{engine}'")
    EnvironmentConfiguration(engine).write(name, root)


def environment_list(root: OptionalRoot = None) -> list[str]:
    """List known environments.

    Args:
        root: The root, or if not given search from the current directory.

    Returns:
        A sorted list of environment names.  The name `empty` will
            always be present.

    """
    root = open_root(root)
    special = ["empty"]
    path = root.path_environment(None)
    found = [x.name for x in path.glob("*")]
    return sorted(special + found)


def environment_delete(name: str, root: OptionalRoot = None) -> None:
    """Delete an environment.

    Args:
        name: The name of the environment to delete.
        root: The root, or if not given search from the current directory.

    Returns:
        Nothing, called for side effects only.
    """
    root = open_root(root)
    if name == "empty":
        msg = "Can't delete the empty environment"
        raise Exception(msg)
    if not environment_exists(name, root):
        if name == "default":
            reason = "it is empty"
        else:
            reason = "it does not exist"
        msg = f"Can't delete environment '{name}', as {reason}"
        raise Exception(msg)
    print(
        f"Attempting to delete environment '{name}'; this might fail if "
        "files are in use on a network share, in which case you should ",
        "try again later",
    )
    shutil.rmtree(str(root.path_environment(name)))


def environment_check(name: str | None, root: OptionalRoot = None) -> str:
    """Validate an environment name for this root.

    This function can be used to ensure that `name` is a reasonable
    environment name to use in your root.  It returns the resolved
    name (selecting between `empty` and `default` if `name` is
    `None`), and errors if the requested environment is not found.

    Args:
        name: The name of the environment to use, or `None` to select
            the appropriate default.
        root: The root, or if not given search from the current directory.

    Returns:
        The resolved environment name.

    """
    root = open_root(root)
    if name is None:
        return "default" if environment_exists("default", root) else "empty"
    if name == "empty" or environment_exists(name, root):
        return name
    msg = f"No such environment '{name}'"
    raise Exception(msg)


def environment_exists(name: str, root: OptionalRoot = None) -> bool:
    """Check if an environment exists.

    Note that this function will return `False` for `empty`, even
    though `empty` is always a valid choice.  We might change this in
    future.

    Args:
        name: The name of the environment to check.
        root: The root, or if not given search from the current directory.

    Returns:
        `True` if the environment exists, otherwise `False`.

    """
    root = open_root(root)
    return root.path_environment(name).exists()


# TODO: move this somewhere less user-facing
def environment_engine(name: str, root: Root) -> EnvironmentEngine:
    use_empty_environment = name == "empty" or (
        name == "default" and not environment_exists(name, root)
    )
    if use_empty_environment:
        cfg = EnvironmentConfiguration("empty")
    else:
        cfg = EnvironmentConfiguration.read(name, root)
    if cfg.engine == "pip":
        return Pip(root, name)
    elif cfg.engine == "empty":
        return Empty(root, name)
    raise NotImplementedError()  # pragma no cover
