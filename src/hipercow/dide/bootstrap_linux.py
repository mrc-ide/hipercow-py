from pathlib import Path
from string import Template

from hipercow.dide.mounts import Mount, _forward_slash
from hipercow.dide.web import DideWebClient
from hipercow.resources import TaskResources

BOOTSTRAP_LINUX = Template(
    r"""#!/bin/bash
echo working directory: $$(pwd)

export PATH=/opt/apps/lmod/lmod/libexec:$$PATH
source /opt/apps/lmod/lmod/init/bash
export LMOD_CMD=/opt/apps/lmod/lmod/libexec/lmod
module use /modules-share/modules/all
module load Python/${version}

export PIPX_HOME=/wpia-hn/Hipercow/bootstrap-py-linux/python-${version}/pipx
export PIPX_BIN_DIR=/wpia-hn/Hipercow/bootstrap-py-linux/python-${version}/bin

echo "Running pipx to install hipercow"
python /wpia-hn/Hipercow/bootstrap-py-linux/in/pipx.pyz install ${args} ${target} > /wpia-hn/Hipercow/bootstrap-py-linux/in/${bootstrap_id}/${version}.log 2>&1

ErrorCode=$$?

echo ERRORLEVEL was $$ErrorCode
if [ $$ErrorCode -eq 0 ]; then
  echo Installation appears to have been successful
else
  echo Installation failed
  exit $$ErrorCode
fi
"""  # noqa: E501
)


def bootstrap_linux_submit(
    bootstrap_id: str,
    version: str,
    mount: Mount,
    client: DideWebClient,
    target: str,
    args: str,
    name: str,
) -> str:
    path = Path("bootstrap-py-linux") / "in" / bootstrap_id / f"{version}.sh"

    path_local = mount.local / path
    path_local.parent.mkdir(parents=True, exist_ok=True)
    with path_local.open("w", newline="\n") as f:
        f.write(_batch_bootstrap_linux(bootstrap_id, version, target, args))

    resources = TaskResources(queue="LinuxNodes")
    return client.submit(_bootstrap_linux_path(path), name, resources)


def _batch_bootstrap_linux(
    bootstrap_id: str,
    version: str,
    target: str,
    args: str,
) -> str:
    data = {
        "bootstrap_id": bootstrap_id,
        "version": version,
        "args": args,
        "target": target,
    }
    return BOOTSTRAP_LINUX.substitute(data)


def _bootstrap_linux_path(path: Path) -> str:
    path_str = _forward_slash(str(path))
    return f"/wpia-hn/Hipercow/{path_str}"
