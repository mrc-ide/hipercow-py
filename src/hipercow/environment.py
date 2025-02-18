import pickle

from hipercow.environments.pip import Pip
from hipercow.root import Root


def environment_create(root: Root, name: str) -> None:
    path = root.path_environment(path)

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(d, f)


def environment_list(root: Root) -> list[str]:
    return list(root.path / "hipercow" / "environments").glob("*")
