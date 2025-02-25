import pickle
import secrets
import time
from dataclasses import dataclass, field

from hipercow.driver import load_driver
from hipercow.environment import environment_engine
from hipercow.root import Root
from hipercow.util import transient_working_directory


@dataclass
class ProvisioningData:
    name: str
    id: str
    cmd: list[str] | None
    time: float = field(default_factory=time.time, init=False)

    def write(self, root: Root) -> None:
        path = root.path_provision_data(self.name, self.id)
        path.parent.mkdir(parents=True, exist_ok=False)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def read(root: Root, name: str, id: str) -> "ProvisioningData":
        with root.path_provision_data(name, id).open("rb") as f:
            return pickle.load(f)


@dataclass
class ProvisioningResult:
    error: Exception | None
    start: float
    end: float = field(default_factory=time.time, init=False)

    def write(self, root: Root, name: str, id: str) -> None:
        path = root.path_provision_result(name, id)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def read(root: Root, name: str, id: str) -> "ProvisioningResult":
        with root.path_provision_result(name, id).open("rb") as f:
            return pickle.load(f)


@dataclass
class ProvisioningRecord:
    data: ProvisioningData
    result: ProvisioningResult | None

    @staticmethod
    def read(root: Root, name: str, id: str) -> "ProvisioningRecord":
        data = ProvisioningData.read(root, name, id)
        try:
            result = ProvisioningResult.read(root, name, id)
        except FileNotFoundError:
            result = None
        return ProvisioningRecord(data, result)


def provision(
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

    id = secrets.token_hex(8)
    ProvisioningData(name, id, cmd).write(root)
    dr.provision(root, name, id)


def provision_run(root: Root, name: str, id: str) -> None:
    if root.path_provision_result(name, id).exists():
        msg = "Provisioning task '{id}' for '{name}' has already been run"
        raise Exception(msg)
    data = ProvisioningData.read(root, name, id)
    env = environment_engine(root, name)
    logfile = root.path_provision_log(name, id)
    start = time.time()
    with transient_working_directory(root.path):
        if not env.exists():
            env.create(filename=logfile)
        try:
            env.provision(data.cmd, filename=logfile)
            ProvisioningResult(None, start).write(root, name, id)
        except Exception as e:
            ProvisioningResult(e, start).write(root, name, id)
            msg = "Provisioning failed"
            raise Exception(msg) from e
