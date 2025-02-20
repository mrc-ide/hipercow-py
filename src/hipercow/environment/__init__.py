import pickle
from dataclasses import dataclass

from hipercow.driver import load_driver
from hipercow.environment.base import Environment, Platform
from hipercow.environment.pip import Pip
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


def engine(root: Root, platform: Platform, name: str) -> Environment:
    cfg = EnvironmentConfiguration.read(root, name)
    if cfg.engine != "pip":
        raise NotImplementedError()  # pragma: no cover
    return Pip(root, platform, name)


def environment_create(root: Root, name: str, engine: str) -> None:
    path = root.path_environment(name)

    if not path.exists():
        if engine != "pip":
            msg = "Only the 'pip' engine is supported"
            raise Exception(msg)
        print(f"Creating environment '{name}'")
        EnvironmentConfiguration(engine).write(root, name)
    else:
        # Once we support multiple engines, or other configuration
        # options, validate here that it has not changed.
        print(f"Environment '{name}' already exists")


def environment_list(root: Root) -> list[str]:
    # We'll possibly always have the 'none' environment, which will
    # prevent any environment being selected?
    return [x.name for x in (root.path / "hipercow" / "environments").glob("*")]


def environment_provision(
    root: Root,
    name: str,
    cmd: list[str] | None,
    *,
    driver: str | None = None,
):
    path_config = root.path_environment_config(name)
    if not path_config.exists():
        msg = f"Environment '{name}' does not exist"
        raise Exception(msg)

    dr = load_driver(root, driver)
    dr.provision(root, name, cmd)
