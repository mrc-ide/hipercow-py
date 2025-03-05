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
    def write(self, root: Root, name: str):
        path = root.path_environment_config(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def read(root: Root, name: str) -> "EnvironmentConfiguration":
        with root.path_environment_config(name).open("rb") as f:
            return pickle.load(f)


# Called 'new' and not 'create' to make it clear that this does not
# actually create the environment, just the definition of that
# environment.
def environment_new(root: Root, name: str, engine: str) -> None:
    path = root.path_environment(name)

    # We might make this friendlier later
    if name == "empty" or path.exists():
        msg = f"Environment '{name}' already exists"
        raise Exception(msg)

    if engine not in {"pip", "empty"}:
        msg = "Only the 'pip' and 'empty' engines are supported"
        raise Exception(msg)

    print(f"Creating environment '{name}' using '{engine}'")
    EnvironmentConfiguration(engine).write(root, name)


def environment_list(root: Root) -> list[str]:
    special = ["empty"]
    path = root.path_environment(None)
    found = [x.name for x in path.glob("*")]
    return sorted(special + found)


def environment_delete(root: Root, name: str) -> None:
    if name == "empty":
        msg = "Can't delete the empty environment"
        raise Exception(msg)
    if not environment_exists(root, name):
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


def environment_check(root: Root, name: str | None) -> str:
    if name is None:
        return "default"
    if name in {"empty", "default"} or environment_exists(root, name):
        return name
    msg = f"No such environment '{name}'"
    raise Exception(msg)


def environment_exists(root: Root, name: str) -> bool:
    return root.path_environment(name).exists()


def environment_engine(root: Root, name: str) -> EnvironmentEngine:
    use_empty_environment = name == "empty" or (
        name == "default" and not environment_exists(root, name)
    )
    if use_empty_environment:
        cfg = EnvironmentConfiguration("empty")
    else:
        cfg = EnvironmentConfiguration.read(root, name)
    if cfg.engine == "pip":
        return Pip(root, name)
    elif cfg.engine == "empty":
        return Empty(root, name)
    raise NotImplementedError()  # pragma no cover
