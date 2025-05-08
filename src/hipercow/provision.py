import secrets
import time

from pydantic import BaseModel, Field

from hipercow.driver import load_driver
from hipercow.environment import environment_engine
from hipercow.root import OptionalRoot, Root, open_root
from hipercow.util import transient_working_directory


class ProvisioningData(BaseModel):
    name: str
    id: str
    cmd: list[str]
    time: float = Field(default_factory=time.time, init=False)


# This bit is an issue; there is no serialiser for exceptions, so we
# need to set something up so that we can serialise this nicely.  The
# simplest bit would be to save it as a massive chunk of base64
# encoded data representing the pickle-dumped exception.  Or we can
# run it through rich and save the text.
class ProvisioningResult(BaseModel):
    error: None | str
    start: float
    end: float = Field(default_factory=time.time, init=False)


class ProvisioningRecord(BaseModel):
    data: ProvisioningData
    result: ProvisioningResult | None


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

    data = ProvisioningData(name=name, id=id, cmd=cmd)
    # TODO: write a small helper for this pattern?
    path = root.path_provision_data(name, id)
    path.parent.mkdir(parents=True, exist_ok=False)
    with path.open("w") as f:
        f.write(data.model_dump_json())

    dr.provision(name, id, root)


def provision_run(name: str, id: str, root: Root) -> None:
    if root.path_provision_result(name, id).exists():
        msg = f"Provisioning task '{id}' for '{name}' has already been run"
        raise Exception(msg)

    with root.path_provision_data(name, id).open() as f:
        data = ProvisioningData.model_validate_json(f.read())

    env = environment_engine(name, root)
    logfile = root.path_provision_log(name, id)
    start = time.time()
    with transient_working_directory(root.path):
        if not env.exists():
            env.create(filename=logfile)
        try:
            env.provision(data.cmd, filename=logfile)
            result = ProvisioningResult(error=None, start=start)
            with root.path_provision_result(name, id).open("w") as f:
                f.write(result.model_dump_json())
        except Exception as e:
            # TODO: we need to get more here on the error; probably
            # some sort of information on the stack trace ideally but
            # that's fairly hard to pull out (but see
            # traceback.format_exception(e) which gives us most of
            # what we might want)
            result = ProvisioningResult(error=str(e), start=start)
            with root.path_provision_result(name, id).open("w") as f:
                f.write(result.model_dump_json())
            msg = "Provisioning failed"
            raise Exception(msg) from e


def provision_history(name: str, root: Root) -> list[ProvisioningRecord]:
    results = [
        _read_provisioning_record(name, x.name, root)
        for x in (root.path_environment(name) / "provision").glob("*")
    ]
    results.sort(key=lambda x: x.data.time)
    return results


def _read_provisioning_record(
    name: str, id: str, root: Root
) -> ProvisioningRecord:
    with root.path_provision_data(name, id).open() as f:
        data = ProvisioningData.model_validate_json(f.read())
    try:
        with root.path_provision_result(name, id).open() as f:
            result = ProvisioningResult.model_validate_json(f.read())
    except FileNotFoundError:
        result = None
    return ProvisioningRecord(data=data, result=result)
