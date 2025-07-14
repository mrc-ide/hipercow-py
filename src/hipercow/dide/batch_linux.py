import datetime
import platform
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

export PATH=/opt/apps/lmod/lmod/libexec:$$PATH
source /opt/apps/lmod/lmod/init/bash
export LMOD_CMD=/opt/apps/lmod/lmod/libexec/lmod
module use /modules-share/modules/all

module load Python/${python_version}

cd ${hipercow_root_path}
echo working directory: $$(pwd)

export HIPERCOW_NO_DRIVERS=1
export HIPERCOW_CORES=$$CCP_NUMCPUS
export REDIS_URL=10.0.2.254

echo this is a single task

/wpia-hn/Hipercow/bootstrap-py-linux/python-${python_version}/bin/hipercow task eval --capture ${task_id}

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

export PATH=/opt/apps/lmod/lmod/libexec:$$PATH
source /opt/apps/lmod/lmod/init/bash
export LMOD_CMD=/opt/apps/lmod/lmod/libexec/lmod
module use /modules-share/modules/all

module load Python/${python_version}

cd ${hipercow_root_path}
echo working directory: $$(pwd)

echo this is a provisioning task

/wpia-hn/Hipercow/bootstrap-py-linux/python-${python_version}/bin/hipercow environment provision-run ${environment_name} ${provision_id}

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


def _linux_dide_path(path_map: PathMap) -> str:
    host = path_map.mount.host.lower()

    # Map from a server name, to the name of the host
    # when mapped on the linux nodes

    linux_hosts = {
        "wpia-san04": "didehomes",
        "qdrive": "didehomes",
        "wpia-hn": "wpia-hn",
        "wpia-hn.hpc": "wpia-hn",
        "wpia-hn2": "wpia-hn2",
        "wpia-hn2.hpc": "wpia-hn2",
    }

    try:
        linux_host = linux_hosts[host]
    except KeyError:
        err = f"Can't resolve {host} on linux node"
        raise NoLinuxMountPointError(err) from None

    # Now the sharename within that host. This is
    # usually path.map.mount.remote, except in the
    # special case of wpia-san04 / qdrive, where we
    # have to remove "homes/"

    linux_share = path_map.mount.remote
    if host in {"wpia-san04", "qdrive"}:
        linux_share = linux_share.split("/")[-1]

    # The folder relative to that share is
    # path_map.relative - if it's ".", then we don't
    # add anything, otherwise we need to add "/"

    rel = path_map.relative
    rel = "" if rel == "." else rel + "/"

    # Final path - note that it ends in a trailing slash,
    # because rel is either empty, or itself ends in `/`

    return f"/{linux_host}/{linux_share}/{rel}"


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
