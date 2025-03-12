import pickle
import secrets
import time
from dataclasses import dataclass, field

from hipercow.driver import load_driver
from hipercow.environment import environment_engine
from hipercow.root import OptionalRoot, Root, open_root
from hipercow.util import transient_working_directory


@dataclass
class ProvisioningData:
    name: str
    id: str
    cmd: list[str]
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

    def write(self, name: str, id: str, root: Root) -> None:
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
    name: str,
    cmd: list[str] | None,
    *,
    driver: str | None = None,
    root: OptionalRoot = None,
) -> None:
    """Provision an environment.

    This function requires that your root has a driver configured
    (with `hipercow.configure`) and an environment created (with
    `hipercow.environment_new`).

    Note that in the commandline tool, this command is grouped into
    the `environment` group; we may move this function into the
    `environment` module in future.

    Args:
        name: The name of the environment to provision

        cmd: Optionally the command to run to do the provisioning. If
            `None` then the environment engine will select an
            appropriate command if it is well defined for your setup.
            The details here depend on the engine.

        driver: The name of the driver to use in provisioning.
            Normally this can be omitted, as `None` (the default) will
            select your driver automatically if only one is
            configured.

        root: The root, or if not given search from the current directory.

    Returns:
        Nothing, called for side effects only.

    """
    root = open_root(root)
    path_config = root.path_environment_config(name)
    if not path_config.exists():
        msg = f"Environment '{name}' does not exist"
        raise Exception(msg)
    dr = load_driver(driver, root)
    # This is a bit gross because we are loading the local platform
    # and not the platform of the target.  We could know that if the
    # driver tells us it (which it could).
    env = environment_engine(name, root)
    id = secrets.token_hex(8)
    with transient_working_directory(root.path):
        cmd = env.check_args(cmd)
    ProvisioningData(name, id, cmd).write(root)
    dr.provision(name, id, root)


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
            ProvisioningResult(None, start).write(name, id, root)
        except Exception as e:
            ProvisioningResult(e, start).write(name, id, root)
            msg = "Provisioning failed"
            raise Exception(msg) from e


def provision_history(name: str, root: Root) -> list[ProvisioningRecord]:
    results = [
        ProvisioningRecord.read(name, x.name, root)
        for x in (root.path_environment(name) / "provision").glob("*")
    ]
    results.sort(key=lambda x: x.data.time)
    return results
