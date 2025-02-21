import datetime
import platform
from string import Template

from hipercow.__about__ import __version__ as version
from hipercow.dide.mounts import PathMap
from hipercow.root import Root

TASK_RUN = Template(
    """@echo off
REM automatically generated
ECHO generated on host: ${hostname}
ECHO generated on date: ${date}
ECHO hipercow(py) version: ${hipercow_version}
ECHO running on: %COMPUTERNAME%

net use I: \\\\wpia-hn\\hipercow /y

${network_shares_create}

${hipercow_root_drive}
cd ${hipercow_root_path}
ECHO working directory: %CD%

set HIPERCOW_NO_DRIVERS=1
set HIPERCOW_CORES=%CCP_NUMCPUS%
set REDIS_URL=10.0.2.254

ECHO this is a single task

I:\\bootstrap-py\\python-311\\bin\\hipercow task eval --capture ${task_id}

@ECHO off
set ErrorCode=%ERRORLEVEL%

@REM We could use hipercow here, I think
if exist hipercow\\tasks\\${task_id_1}\\${task_id_2}\\status-success (
  set TaskStatus=0
) else (
  set TaskStatus=1
)

ECHO ERRORLEVEL was %ErrorCode%

ECHO Cleaning up
%SystemDrive%

${network_shares_delete}

net use I: /delete /y

if %ErrorCode% neq 0 (
  ECHO Task failed catastrophically
  EXIT /b %ErrorCode%
)

if %TaskStatus% == 0 (
  ECHO Task completed successfully!
  ECHO Quitting
) else (
  ECHO Task did not complete successfully
  EXIT /b 1
)"""
)

PROVISION = Template(
    """@echo off
REM automatically generated
ECHO generated on host: ${hostname}
ECHO generated on date: ${date}
ECHO hipercow(py) version: ${hipercow_version}
ECHO running on: %COMPUTERNAME%

net use I: \\\\wpia-hn\\hipercow /y

${network_shares_create}

${hipercow_root_drive}
cd ${hipercow_root_path}
ECHO working directory: %CD%

ECHO this is a provisioning task

[[call whatever we need here to do the installation]]

@ECHO off
%SystemDrive%
set ErrorCode=%ERRORLEVEL%

ECHO ERRORLEVEL was %ErrorCode%

ECHO Cleaning up
%SystemDrive%

${network_shares_delete}

net use I: /delete /y

set ERRORLEVEL=%ErrorCode%

if %ERRORLEVEL% neq 0 (
  ECHO Error running provisioning
  EXIT /b %ERRORLEVEL%
)

@ECHO Quitting
"""
)


# In a future version, we might prefer to use a configuration object,
# perhaps extracted from the root, rather than the actual argument for
# the path mapping, but this iterates towards something that we can
# start running on the cluster itself before everything is ready.
#
# There's two bits here where we faff about with the unc path - we
# needf the relative path and the absolute path to the task directory
# and we build the unc base path twice (once with slash normalisation,
# the other without).
def write_batch_task_run(task_id: str, path_map: PathMap, root: Root) -> str:
    data = _template_data_task_run(task_id, path_map)
    path = str(root.path_task(task_id, relative=True) / "task_run.bat")
    path = path.replace("\\", "/")
    rel = path_map.relative
    unc = f"//{path_map.mount.host}/{path_map.mount.remote}/{rel}/{path}"
    with (root.path / path).open("w") as f:
        f.write(TASK_RUN.substitute(data))
    return unc


def write_batch_provision(
    name: str, provision_id: str, path_map: PathMap, root: Root
) -> str:
    data = _template_data_provision(name, provision_id, path_map)
    path = str(
        root.path_environment(name, relative=True)
        / "batch"
        / f"{provision_id}.bat"
    )
    path = path.replace("\\", "/")
    rel = path_map.relative
    unc = f"//{path_map.mount.host}/{path_map.mount.remote}/{rel}/{path}"
    with (root.path / path).open("w") as f:
        f.write(PROVISION.substitute(data))
    return unc


def _template_data_core(path_map: PathMap) -> dict[str, str]:
    host = path_map.mount.host
    unc_path = f"//{host}/{path_map.mount.remote}".replace("/", "\\")
    root_drive = path_map.remote
    root_path = "/" + path_map.relative

    network_shares_create = f"net use {root_drive} {unc_path} /y"
    network_shares_delete = f"net use {root_drive} /delete /y"

    return {
        "hostname": platform.node(),
        "date": str(datetime.datetime.now(tz=datetime.timezone.utc)),
        "hipercow_version": version,
        "hipercow_root_drive": root_drive,
        "hipercow_root_path": root_path,
        "network_shares_create": network_shares_create,
        "network_shares_delete": network_shares_delete,
    }


def _template_data_task_run(task_id, path_map: PathMap) -> dict[str, str]:
    return _template_data_core(path_map) | {
        "task_id": task_id,
        "task_id_1": task_id[:2],
        "task_id_2": task_id[2:],
    }


def _template_data_provision(
    name: str, id: str, path_map: PathMap
) -> dict[str, str]:
    return _template_data_core(path_map) | {"name": name, "provision_id": id}
