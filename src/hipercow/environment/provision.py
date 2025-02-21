import pickle
import secrets
import time
from dataclasses import dataclass, field

from hipercow.driver import load_driver
from hipercow.environment import engine
from hipercow.root import Root
from hipercow.util import transient_working_directory


@dataclass
class ProvisioningData:
    name: str
    cmd: list[str] | None
    id: str = field(default_factory=lambda: secrets.token_hex(8), init=False)
    time: float = field(default_factory=time.time, init=False)

    def write(self, root: Root) -> None:
        path = root.path_environment_provision_data(self.name, self.id)
        path.parent.mkdir(parents=True, exist_ok=False)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def read(root: Root, name: str, id: str) -> "ProvisioningData":
        with root.path_environment_provision_data(name, id).open("rb") as f:
            return pickle.load(f)


@dataclass
class ProvisioningResult:
    data: ProvisioningData
    error: Exception | None
    start: float
    end: float = field(default_factory=time.time, init=False)

    def write(self, root: Root) -> None:
        data = self.data
        path = root.path_environment_provision_result(data.name, data.id)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def read(root: Root, name: str, id: str) -> "ProvisioningResult":
        with root.path_environment_provision_result(name, id).open("rb") as f:
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
    dr = load_driver(root, driver)

    data = ProvisioningData(name, cmd)
    data.write(root)
    dr.provision(root, name, data.id)


def environment_provision_run(root: Root, name: str, id: str) -> None:
    data = ProvisioningData.read(root, name, id)
    env = engine(root, name)
    logfile = root.path_environment_provision_log(name, id)
    start = time.time()
    with transient_working_directory(root.path):
        if not env.exists():
            env.create(filename=logfile)
        try:
            env.provision(data.cmd, filename=logfile)
            ProvisioningResult(data, None, start).write(root)
        except Exception as e:
            ProvisioningResult(data, e, start).write(root)
            msg = "Provisioning failed"
            raise Exception(msg) from e


def environment_provision_history(
    root: Root, name: str
) -> list[ProvisioningResult]:
    results = [
        ProvisioningResult.read(root, name, x.name)
        for x in (root.path_environment(name) / "provision").glob("*")
    ]
    results.sort(key=lambda x: x.data.time)
    return results
