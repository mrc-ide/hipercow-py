import datetime
import platform
from string import Template

from hipercow.__about__ import __version__ as version
from hipercow.dide.configuration import DideConfiguration
from hipercow.dide.mounts import PathMap, _forward_slash
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


def write_batch_task_run_linux(
    task_id: str, config: DideConfiguration, root: Root
) -> str:
    data = _template_data_task_run_linux(task_id, config)
    path = root.path_task(task_id, relative=True) / "task_run.sh"
    with (root.path / path).open("w", newline="\n") as f:
        f.write(TASK_RUN_SH.substitute(data))
    return data["hipercow_root_path"] + "/" + _forward_slash(str(path))


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


# Here we are converting a fully-qualified path into
# how they appear on the linux nodes. Specifically:-

# \\wpia-san04\homes\wrh1 => /didehomes/wrh1
# \\wpia-san04.dide.local\homes\wrh1 => /didehomes/wrh1
# \\wpia-san04.dide.ic.ac.uk\homes\wrh1 => /didehomes/wrh1

# \\qdrive\homes\wrh1 => /didehomes/wrh1
# \\qdrive.dide.ic.ac.uk\homes\wrh1 => /didehomes/wrh1

# \\wpia-hn\alice => /wpia-hn/alice
# \\wpia-hn.hpc.dide.ic.ac.uk\alice => /wpia-hn/alice

# \\wpia-hn2\bob => /wpia-hn2/bob
# \\wpia-hn2.hpc.dide.ic.ac.uk\bob => /wpia-hn2/bob


class NoLinuxMountPointError(Exception):
    pass


def _linux_dide_path(path_map: PathMap) -> str:
    host = path_map.mount.host.lower()
    if host in {"wpia-san04", "qdrive"}:
        linux_base = "/didehomes" + "/" + path_map.mount.remote.split("/")[-1]
    elif host in {"wpia-hn", "wpia-hn.hpc"}:
        linux_base = "/wpia-hn" + "/" + path_map.mount.remote
    elif host in {"wpia-hn2", "wpia-hn2.hpc"}:
        linux_base = "/wpia-hn2" + "/" + path_map.mount.remote
    else:
        err = f"Can't resolve {host} on linux node"
        raise NoLinuxMountPointError(err)
    rel = path_map.relative
    rel = "" if rel == "." else rel + "/"
    return linux_base + "/" + rel
