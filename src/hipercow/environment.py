import pickle

from hipercow.environments.pip import Pip
from hipercow.root import Root


def create(root: Root, name: str, method: str) -> None:
    path = root.path_environment(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(d, f)
