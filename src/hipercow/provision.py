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
    def read(name: str, id: str, root: Root) -> "ProvisioningData":
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
    def read(name: str, id: str, root: Root) -> "ProvisioningResult":
        with root.path_provision_result(name, id).open("rb") as f:
            return pickle.load(f)


@dataclass
class ProvisioningRecord:
    data: ProvisioningData
    result: ProvisioningResult | None

    @staticmethod
    def read(name: str, id: str, root: Root) -> "ProvisioningRecord":
        data = ProvisioningData.read(name, id, root)
        try:
            result = ProvisioningResult.read(name, id, root)
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
    dr = load_driver(driver, root)

    id = secrets.token_hex(8)
    ProvisioningData(name, id, cmd).write(root)
    dr.provision(root, name, id)


def provision_run(name: str, id: str, root: Root) -> None:
    if root.path_provision_result(name, id).exists():
        msg = f"Provisioning task '{id}' for '{name}' has already been run"
        raise Exception(msg)
    data = ProvisioningData.read(name, id, root)
    env = environment_engine(name, root)
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


def provision_history(name: str, root: Root) -> list[ProvisioningRecord]:
    results = [
        ProvisioningRecord.read(name, x.name, root)
        for x in (root.path_environment(name) / "provision").glob("*")
    ]
    results.sort(key=lambda x: x.data.time)
    return results
