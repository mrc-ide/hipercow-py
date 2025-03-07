import pickle
import shutil
from dataclasses import dataclass

from hipercow.environment_engines import (
    Empty,
    EnvironmentEngine,
    Pip,
)
from hipercow.root import Root


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
def environment_new(name: str, engine: str, root: Root) -> None:
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


def environment_list(root: Root) -> list[str]:
    special = ["empty"]
    path = root.path_environment(None)
    found = [x.name for x in path.glob("*")]
    return sorted(special + found)


def environment_delete(name: str, root: Root) -> None:
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


def environment_check(name: str | None, root: Root) -> str:
    if name is None:
        return "default" if environment_exists("default", root) else "empty"
    if name == "empty" or environment_exists(name, root):
        return name
    msg = f"No such environment '{name}'"
    raise Exception(msg)


def environment_exists(name: str, root: Root) -> bool:
    return root.path_environment(name).exists()


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
