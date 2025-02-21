import pickle
import secrets
import time
from dataclasses import dataclass, field

from hipercow.driver import load_driver
from hipercow.environment.base import Environment, Platform
from hipercow.environment.empty import Empty
from hipercow.environment.pip import Pip
from hipercow.root import Root
from hipercow.util import transient_working_directory


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


def engine(root: Root, name: str) -> Environment:
    use_empty_environment = name == "empty" or (
        name == "default" and not environment_exists(root, name)
    )
    platform = Platform.local()
    if use_empty_environment:
        return Empty(root, platform, name)
    cfg = EnvironmentConfiguration.read(root, name)
    if cfg.engine == "pip":
        return Pip(root, platform, name)

    raise NotImplementedError()  # pragma: no cover


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


def environment_check(root: Root, name: str | None) -> str:
    if name is None:
        return "default"
    if name in {"empty", "default"} or environment_exists(root, name):
        return name
    msg = f"No such environment '{name}'"
    raise Exception(msg)


def _new_provisioning_id() -> str:
    return secrets.token_hex(8)


@dataclass
class ProvisioningData:
    name: str
    cmd: list[str] | None
    id: str = field(default_factory=_new_provisioning_id, init=False)
    time: float = field(default_factory=time.time, init=False)

    def write(self, root: Root):
        path = root.path_environment_provision_data(self.name, self.id)
        path.parent.mkdir(parents=True, exist_ok=False)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def read(root: Root, name: str, id: str) -> "ProvisioningData":
        with root.path_environment_provision_data(name, id).open("rb") as f:
            return pickle.load(f)


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

    data = ProvisioningData(name, cmd)
    data.write(root)

    dr = load_driver(root, driver)
    dr.provision(root, name, data.id)


def environment_provision_run(root: Root, name: str, id: str) -> None:
    data = ProvisioningData.read(root, name, id)
    env = engine(root, name)
    with transient_working_directory(root.path):
        if not env.exists():
            env.create()
        env.provision(data.cmd)


def environment_exists(root: Root, name: str) -> bool:
    return root.path_environment(name).exists()
