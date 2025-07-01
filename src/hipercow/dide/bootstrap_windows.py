from pathlib import Path
from string import Template

from hipercow.dide.mounts import Mount, _backward_slash
from hipercow.dide.web import DideWebClient
from hipercow.resources import TaskResources

BOOTSTRAP_WINDOWS = Template(
    r"""@ECHO on
ECHO working directory: %CD%
call set_python_${version2}_64
set PIPX_HOME=\\wpia-hn-app\hipercow\bootstrap-py-windows\python-${version}\pipx
set PIPX_BIN_DIR=\\wpia-hn-app\hipercow\bootstrap-py-windows\python-${version}\bin

echo "Running pipx to install hipercow"
python \\wpia-hn-app\hipercow\bootstrap-py-windows\in\pipx.pyz install ${args} ${target} > \\wpia-hn-app\hipercow\bootstrap-py-windows\in\${bootstrap_id}\${version}.log 2>&1
set ErrorCode=%ERRORLEVEL%
@ECHO ERRORLEVEL was %ErrorCode%
if %ErrorCode% == 0 (
  @ECHO Installation appears to have been successful
) else (
  @ECHO Installation failed
  EXIT /b %ErrorCode%
)
"""  # noqa: E501
)


def bootstrap_windows_submit(
    bootstrap_id: str,
    version: str,
    mount: Mount,
    client: DideWebClient,
    target: str,
    args: str,
    name: str,
) -> str:
    path = Path("bootstrap-py-windows") / "in" / bootstrap_id / f"{version}.bat"

    path_local = mount.local / path
    path_local.parent.mkdir(parents=True, exist_ok=True)
    with path_local.open("w") as f:
        f.write(_batch_bootstrap_windows(bootstrap_id, version, target, args))

    resources = TaskResources(queue="AllNodes")  # not BuildQueue, for now
    return client.submit(_bootstrap_windows_path(path), name, resources)


def _batch_bootstrap_windows(
    bootstrap_id: str,
    version: str,
    target: str,
    args: str,
) -> str:
    data = {
        "bootstrap_id": bootstrap_id,
        "version": version,
        "version2": version.replace(".", ""),  # Wes: update the batch filenames
        "args": args,
        "target": target,
    }
    return BOOTSTRAP_WINDOWS.substitute(data)


def _bootstrap_windows_path(path: Path) -> str:
    path_str = _backward_slash(str(path))
    return f"\\\\wpia-hn\\hipercow\\{path_str}"
