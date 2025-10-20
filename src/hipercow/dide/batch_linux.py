import datetime
import platform
from pathlib import Path
from string import Template

from taskwait import taskwait

from hipercow import ui
from hipercow.__about__ import __version__ as version
from hipercow.dide.configuration import DideConfiguration
from hipercow.dide.mounts import PathMap, _forward_slash
from hipercow.dide.provision import ProvisionWaitWrapper
from hipercow.dide.web import DideWebClient
from hipercow.resources import TaskResources
from hipercow.root import Root

TASK_RUN_SH = Template(
    r"""#!/bin/bash
# automatically generated

echo generated on host: ${hostname}
echo generated on date: ${date}
echo hipercow-py version: ${hipercow_version}
echo running on: $$(hostname -f)

source /etc/profile

module use /modules/modules/all

module load Python/${python_version}

cd ${hipercow_root_path}
echo working directory: $$(pwd)

export HIPERCOW_NO_DRIVERS=1
export HIPERCOW_CORES=$$CCP_NUMCPUS
export REDIS_URL=10.0.2.254

echo this is a single task

/mnt/cluster/Hipercow/bootstrap-py-linux/python-${python_version}/bin/hipercow task eval --capture ${task_id}

ErrorCode=$$?

# We could use hipercow here, I think
if [ -f hipercow/py/tasks/${task_id_1}/${task_id_2}/status-success ]; then
  TaskStatus=0
else
  TaskStatus=1
fi

echo ERRORLEVEL was $$ErrorCode


if [ $$ErrorCode -ne 0 ]; then
  echo Task failed catastrophically
  exit $$ErrorCode
fi

if [ $$TaskStatus -eq 0 ]; then
  echo Task completed successfully!
  echo Quitting
else
  echo Task did not complete successfully
  exit 1
fi

"""  # noqa: E501
)


PROVISION_SH = Template(
    r"""#!/bin/bash
# automatically generated

echo generated on host: ${hostname}
echo generated on date: ${date}
echo hipercow-py version: ${hipercow_version}
echo running on: $$(hostname -f)

source /etc/profile

module use /modules/modules/all

module load Python/${python_version}

cd ${hipercow_root_path}
echo working directory: $$(pwd)

echo this is a provisioning task

/mnt/cluster/Hipercow/bootstrap-py-linux/python-${python_version}/bin/hipercow environment provision-run ${environment_name} ${provision_id}

ErrorCode=$$?

echo ERRORLEVEL was $$ErrorCode

if [ $$ErrorCode -ne 0 ]; then
  echo Error running provisioning
  exit $$ErrorCode
fi

echo Quitting
"""  # noqa: E501
)


def write_batch_task_run_linux(
    task_id: str, config: DideConfiguration, root: Root
) -> str:
    data = _template_data_task_run_linux(task_id, config)
    path = root.path_task(task_id, relative=True)
    (root.path / path).mkdir(parents=True, exist_ok=True)
    path = path / "task_run.sh"
    with (root.path / path).open("w", newline="\n") as f:
        f.write(TASK_RUN_SH.substitute(data))
    return data["hipercow_root_path"] + _forward_slash(str(path))


def write_batch_provision_linux(
    name: str, provision_id: str, config: DideConfiguration, root: Root
) -> str:
    data = _template_data_provision_linux(name, provision_id, config)
    path = root.path_provision(name, provision_id, relative=True)
    (root.path / path).mkdir(parents=True, exist_ok=True)
    path = path / "run.sh"
    with (root.path / path).open("w", newline="\n") as f:
        f.write(PROVISION_SH.substitute(data))
    return data["hipercow_root_path"] + _forward_slash(str(path))


def _template_data_core_linux(config: DideConfiguration) -> dict[str, str]:
    path_map = config.path_map
    return {
        "hostname": platform.node(),
        "date": str(datetime.datetime.now(tz=datetime.timezone.utc)),
        "python_version": config.python_version,
        "hipercow_version": version,
        "hipercow_root_path": _linux_dide_path(path_map),
    }


def _template_data_task_run_linux(
    task_id, config: DideConfiguration
) -> dict[str, str]:
    return _template_data_core_linux(config) | {
        "task_id": task_id,
        "task_id_1": task_id[:2],
        "task_id_2": task_id[2:],
    }


def _template_data_provision_linux(
    name: str, id: str, config: DideConfiguration
) -> dict[str, str]:
    return _template_data_core_linux(config) | {
        "environment_name": name,
        "provision_id": id,
    }


class NoLinuxMountPointError(Exception):
    pass


def _unify_host(host) -> str:
    host = host.lower()
    if host in [
        "wpia-san04",
        "wpia-san04.dide.ic.ac.uk",
        "wpia-san04.dide.local",
        "qdrive",
        "qdrive.dide.ic.ac.uk",
        "qdrive.dide.local"
    ]:
        return "qdrive"

    if host in [
        "wpia-hn",
        "wpia-hn.dide.ic.ac.uk",
        "wpia-hn.hpc",
        "wpia-hn.hpc.dide.ic.ac.uk",
        "wpia-hn.dide.local",
        "wpia-hn.hpc.dide.local"
    ]:
        return "wpia-hn"

    if host in [
        "wpia-hn2",
        "wpia-hn2.dide.ic.ac.uk",
        "wpia-hn2.hpc",
        "wpia-hn2.hpc.dide.ic.ac.uk",
        "wpia-hn2.dide.local",
        "wpia-hn2.hpc.dide.local"
    ]:
        return "wpia-hn2"

    err = f"Unrecognised host: {host} on linux node"
    raise NoLinuxMountPointError(err) from None


def _attempt_check_exists_unc(unc_path):
    if platform.system() != "Windows":
        return True
    try:
        return Path(unc_path).exists()
    except OSError:
        return False


def _linux_dide_path(path_map: PathMap) -> str:

    # This is quite a fiddly function to convert from the local
    # mount.host and mount.remote into the mount on a
    # linux node. It is fiddly because...

    # (1) There are aliases of mount.host for the same machine

    # (2) For the host wpia-hn2, which linux mount to use
    #     also depends on the first part of mount.remote.

    # (3) We have some share users which exist in the
    #     multi-user share, but they refer to them as if
    #     they are not. For example,
    #     \\wpia-hn\Hipercow actually points to
    #     \\wpia-hn\cluster-storage\Hipercow - and for
    #     linux are only using multi-user - so /mnt/cluster/Hipercow

    # (4) The above is just about the local mount. We then also have a
    #     `rel` - relative path within that mount, which might be `.` or
    #     might be more folders.

    # Get an unambiguous hostname, wpia-hn, wpia-hn2 or qdrive

    host = _unify_host(path_map.mount.host)

    # Separate the first part of the rest of the mount, from
    # the remaining directories - we want it to end with /

    rest_of_path = path_map.mount.remote
    head_tail = path_map.mount.remote.split("/", 1)
    share_head = head_tail[0]
    share_tail = head_tail[1] if len(head_tail) > 1 else None
    share_tail = (share_tail.rstrip("/") + "/") if share_tail else ""

    # If the relative path (rel) is `.` then we ignore it.
    # If it has more folders, then append, and add trailing /

    rel = path_map.relative
    rel = "" if rel == "." else f"{rel}/"

    # First deal with qdrive, which always has `homes/username` as
    # the remote path, which we translate to /mnt/homes/username

    if host == "qdrive" and share_head == "homes":
        return f"/mnt/homes/{share_tail}{rel}"

    # Now deal with wpia-hn and wpia-hn2 when the multi-user share
    # is mounted.

    if host == "wpia-hn" and share_head == "cluster-storage":
        return f"/mnt/cluster/{share_tail}{rel}"

    if host == "wpia-hn2" and share_head == "climate-storage":
        return f"/mnt/vimc-cc1/{share_tail}{rel}"

    if host == "wpia-hn2" and share_head == "vimc-cc2-storage":
        return f"/mnt/vimc-cc2/{share_tail}{rel}"

    # On wpia-hn we can also have \\wpia-hn\share for a number of
    # paths where \\wpia-hn\cluster-storage\share exists, and is what
    # the first link also points to. Do this translation if we can.
    # We can check whether the network path exists on windows, but not
    # so easily on other operating sytems where we'd need it already
    # mounted.

    if host == "wpia-hn":
        unc = f"\\\\wpia-hn.hpc.dide.ic.ac.uk\\cluster-storage\\{share_head}"
        if _attempt_check_exists_unc(unc):
            return f"/mnt/cluster/{share_head}{rel}"

    # If we reach here, we've failed to return a valid linux cluster mount.

    err = f"Can't resolve path {rest_of_path} on host {host} on linux node."
    raise NoLinuxMountPointError(err) from None


def _dide_provision_linux(
    name: str, id: str, config: DideConfiguration, cl: DideWebClient, root: Root
):
    unc = write_batch_provision_linux(name, id, config, root)
    resources = TaskResources(queue="LinuxNodes")
    dide_id = cl.submit(unc, f"{name}/{id}", resources=resources)
    task = ProvisionWaitWrapper(root, name, id, cl, dide_id)
    res = taskwait(task)
    dt = round(res.end - res.start, 2)
    if res.status == "failure":
        path_log = root.path_provision_log(name, id, relative=True)
        ui.alert_danger(f"Provisioning failed after {dt}s!")
        ui.blank_line()
        ui.text("Logs, if produced, may be visible above")
        ui.text("A copy of all logs is available at:")
        ui.text(f"    {path_log}")
        ui.blank_line()
        dide_log = cl.log(dide_id)
        ui.logs("Logs from the cluster", dide_log)
        msg = "Provisioning failed"
        raise Exception(msg)
    else:
        ui.alert_success(f"Provisioning completed in {dt}s")
