import datetime
import platform
import re
from pathlib import Path
from string import Template

from taskwait import taskwait

from hipercow import ui
from hipercow.__about__ import __version__ as version
from hipercow.dide.configuration import DideConfiguration
from hipercow.dide.mounts import PathMap, _backward_slash, _forward_slash
from hipercow.dide.provision import ProvisionWaitWrapper
from hipercow.dide.web import DideWebClient
from hipercow.resources import TaskResources
from hipercow.root import Root

TASK_RUN_BAT = Template(
    r"""@echo off
REM automatically generated
ECHO generated on host: ${hostname}
ECHO generated on date: ${date}
ECHO hipercow(py) version: ${hipercow_version}
ECHO running on: %COMPUTERNAME%

net use I: \\wpia-hn-app\hipercow /y

call setGit.bat

${network_shares_create}

${hipercow_root_drive}
cd ${hipercow_root_path}
ECHO working directory: %CD%

set HIPERCOW_NO_DRIVERS=1
set HIPERCOW_CORES=%CCP_NUMCPUS%
set REDIS_URL=10.0.2.254

ECHO this is a single task

I:\bootstrap-py-windows\python-${python_version}\bin\hipercow task eval --capture ${task_id}

@ECHO off
set ErrorCode=%ERRORLEVEL%

@REM We could use hipercow here, I think
if exist hipercow\py\tasks\${task_id_1}\${task_id_2}\status-success (
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
)"""  # noqa: E501
)

PROVISION_BAT = Template(
    r"""@echo off
REM automatically generated
ECHO generated on host: ${hostname}
ECHO generated on date: ${date}
ECHO hipercow(py) version: ${hipercow_version}
ECHO running on: %COMPUTERNAME%

net use I: \\wpia-hn-app\hipercow /y

call setGit.bat

${network_shares_create}

${hipercow_root_drive}
cd ${hipercow_root_path}
ECHO working directory: %CD%

ECHO this is a provisioning task

I:\bootstrap-py-windows\python-${python_version}\bin\hipercow environment provision-run ${environment_name} ${provision_id}

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
"""  # noqa: E501
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
def write_batch_task_run_win(
    task_id: str, config: DideConfiguration, root: Root
) -> str:
    data = _template_data_task_run_win(task_id, config)
    path_map = config.path_map
    path = root.path_task(task_id, relative=True) / "task_run.bat"
    unc = _unc_path(path_map, path)
    with (root.path / path).open("w") as f:
        f.write(TASK_RUN_BAT.substitute(data))
    return unc


def write_batch_provision_win(
    name: str, provision_id: str, config: DideConfiguration, root: Root
) -> str:
    path_map = config.path_map
    data = _template_data_provision_win(name, provision_id, config)
    path = root.path_provision(name, provision_id, relative=True) / "run.bat"
    unc = _unc_path(path_map, path)

    path_abs = root.path / path
    path_abs.parent.mkdir(parents=True, exist_ok=True)
    with (path_abs).open("w") as f:
        f.write(PROVISION_BAT.substitute(data))
    return unc


def _template_data_core_win(config: DideConfiguration) -> dict[str, str]:
    path_map = config.path_map
    host = _clean_host(path_map.mount.host)
    unc_path = _backward_slash(f"//{host}/{path_map.mount.remote}")
    root_drive = path_map.remote
    root_path = _backward_slash("/" + path_map.relative)

    network_shares_create = f"net use {root_drive} {unc_path} /y"
    network_shares_delete = f"net use {root_drive} /delete /y"

    return {
        "hostname": platform.node(),
        "date": str(datetime.datetime.now(tz=datetime.timezone.utc)),
        "python_version": config.python_version,
        "hipercow_version": version,
        "hipercow_root_drive": root_drive,
        "hipercow_root_path": root_path,
        "network_shares_create": network_shares_create,
        "network_shares_delete": network_shares_delete,
    }


def _template_data_task_run_win(
    task_id, config: DideConfiguration
) -> dict[str, str]:
    return _template_data_core_win(config) | {
        "task_id": task_id,
        "task_id_1": task_id[:2],
        "task_id_2": task_id[2:],
    }


def _template_data_provision_win(
    name: str, id: str, config: DideConfiguration
) -> dict[str, str]:
    return _template_data_core_win(config) | {
        "environment_name": name,
        "provision_id": id,
    }


def _unc_path(path_map: PathMap, path: Path) -> str:
    path_str = _forward_slash(str(path))
    rel = path_map.relative
    rel = "" if rel == "." else rel + "/"
    host = _clean_host(path_map.mount.host)
    ret = f"//{host}/{path_map.mount.remote}/{rel}{path_str}"
    return _backward_slash(ret)


def _clean_host(host: str) -> str:
    return re.sub("\\.hpc$", "-app", host)


def _dide_provision_win(
    name: str, id: str, config: DideConfiguration, cl: DideWebClient, root: Root
):
    unc = write_batch_provision_win(name, id, config, root)
    resources = TaskResources(queue="BuildQueue")
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
