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

net use I: \\\\wpia-hn\\hipercow

${network_shares_create}

${hipercow_root_drive}
cd ${hipercow_root_path}
ECHO working directory: %CD%

set HIPERCOW_NO_DRIVERS=1
set HIPERCOW_CORES=%CCP_NUMCPUS%
set REDIS_URL=10.0.2.254

ECHO this is a single task

I:\\py\\hipercow task eval --capture ${task_id}

@ECHO off
set ErrorCodeTask=%ERRORLEVEL%

@REM We could use hipercow here, I think
if exist hipercow\\tasks\\${task_id_1}\\${task_id_2}\\status-success (
  set TaskStatus=0
) else (
  set TaskStatus=1
)

ECHO ERRORLEVEL was %ErrorCodeTask%

ECHO Cleaning up
%SystemDrive%

${network_shares_delete}

net use I: /delete /y

if %ErrorCodeTask% neq 0 (
  ECHO Task failed catastrophically
  EXIT /b %ErrorCodeTask%
)

if %TaskStatus% == 0 (
  ECHO Task completed successfully!
  ECHO Quitting
) else (
  ECHO Task did not complete successfully
  EXIT /b 1
)"""
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
    path = root.path_task(task_id, relative=True) / "task_run.bat"
    rel = path_map.relative.replace("\\", "/")
    unc = f"//{path_map.mount.host}/{path_map.mount.remote}/{rel}/{path}"
    with (root.path / path).open("w") as f:
        f.write(TASK_RUN.substitute(data))
    return unc


def _template_data_task_run(task_id, path_map: PathMap) -> dict:
    host = path_map.mount.host
    unc_path = f"//{host}/{path_map.mount.remote}".replace("/", "\\")
    root_drive = path_map.remote
    root_path = "/" + path_map.relative

    network_shares_create = f"net use {unc_path} {root_drive} /y"
    network_shares_delete = f"net use {root_drive} /delete /y"

    return {
        "hostname": platform.node(),
        "date": str(datetime.datetime.now(tz=datetime.timezone.utc)),
        "hipercow_version": version,
        "task_id": task_id,
        "task_id_1": task_id[:2],
        "task_id_2": task_id[2:],
        "hipercow_root_drive": root_drive,
        "hipercow_root_path": root_path,
        "network_shares_create": network_shares_create,
        "network_shares_delete": network_shares_delete,
    }
