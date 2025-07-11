from dataclasses import dataclass
from pathlib import Path

import requests

from hipercow import ui
from hipercow.dide.auth import Credentials, check_access, fetch_credentials
from hipercow.dide.mounts import detect_mounts, remap_path
from hipercow.driver import load_driver
from hipercow.root import Root, open_root
from hipercow.util import Result

_DOCS = "https://mrc-ide.github.io/hipercow-py"


@dataclass
class DideCheckResult:
    credentials: Result
    connection: Result
    path: Result
    root: Result

    def __bool__(self) -> bool:
        return (
            bool(self.credentials)
            and bool(self.connection)
            and bool(self.path)
            and bool(self.root)
        )


def dide_check(path: Path | None = None) -> None:
    """Check that everything is correctly configured to use hipercow."""
    path = path or Path.cwd()

    result = DideCheckResult(
        _dide_check_credentials(),
        _dide_check_connection(),
        _dide_check_path(path),
        _dide_check_root(path),
    )
    if not result:
        msg = "You have issues to address before using hipercow"
        raise Exception(msg)
    ui.alert_success("You look good to go!")


def _dide_check_credentials() -> Result:
    ui.alert_arrow("Checking DIDE credentials")
    try:
        credentials = fetch_credentials()
        ui.alert_success("Found DIDE credentials", indent=4)
        ui.alert_info(f"Your username is '{credentials.username}'", indent=4)
        return _dide_check_access(credentials)
    except Exception as e:
        ui.alert_danger(str(e), indent=4)
        ui.alert_see_also(f"{_DOCS}/dide/#authentication-with-dide", indent=4)
        return Result.err(e)


def _dide_check_access(credentials: Credentials) -> Result:
    try:
        # TODO: we should break this up a little more and separate out
        # login-failure from access-failure.
        check_access(credentials)
        ui.alert_success("DIDE credentials are correct", indent=4)
        return Result.ok()
    except Exception as e:
        ui.alert_danger(str(e), indent=4)
        ui.alert_see_also(f"{_DOCS}/dide/#authentication-with-dide", indent=4)
        return Result.err(e)


def _dide_check_connection() -> Result:
    ui.alert_arrow("Checking network connections")
    try:
        url = "https://vault.dide.ic.ac.uk:8200"
        requests.head(url, timeout=1)
        ui.alert_success("Connection to private network is working", indent=4)
        return Result.ok()
    except Exception as e:
        ui.alert_danger(
            "Failed to make connection to the private network", indent=4
        )
        ui.alert_info("Please check that you have ZScalar enabled", indent=4)
        ui.alert_see_also(f"{_DOCS}/dide/#networks", indent=4)
        return Result.err(e)


def _dide_check_path(path: Path) -> Result:
    ui.alert_arrow("Checking paths")
    mounts = detect_mounts()
    try:
        map = remap_path(path, mounts)
        ui.alert_success("Path looks like it is on a network share", indent=4)
        ui.alert_info(f"Using '{path}'", indent=4)
        ui.alert_info(
            f"This is '{map.mount.remote}' on '{map.mount.host}'", indent=4
        )
        return Result.ok()
    except Exception as e:
        ui.alert_danger("Failed to map path to a network share", indent=4)
        ui.alert_info(str(e), indent=4)
        ui.alert_see_also(f"{_DOCS}/dide/#filesystems-and-paths", indent=4)
        return Result.err(e)


def _dide_check_root(path: Path) -> Result:
    ui.alert_arrow("Checking hipercow root")
    try:
        root = open_root(path)
        ui.alert_success(f"hipercow is initialised at '{root.path}'", indent=4)
        return _dide_check_root_configured(root)
    except Exception as e:
        ui.alert_danger("hipercow is not initialised", indent=4)
        ui.alert_info(
            "You can run 'hipercow init' to initialise the root", indent=4
        )
        ui.alert_see_also(f"{_DOCS}/introduction/#initialisation", indent=4)
        return Result.err(e)


def _dide_check_root_configured(root: Root) -> Result:
    try:
        load_driver("dide-windows", root)
        ui.alert_success(
            "hipercow is configured to use 'dide-windows'", indent=4
        )
        return Result.ok()
    except Exception as e_win:
        try:
            load_driver("dide-linux", root)
            ui.alert_success(
                "hipercow is configured to use 'dide-linux'", indent=4
            )
            return Result.ok()
        except Exception as e_linux:
            ui.alert_danger(
                "hipercow is not configured with a valid driver.", indent=4
            )
            ui.alert_info(
                "Run 'hipercow driver configure dide-windows' or 'dide-linux' to configure the root",  # noqa: E501
                indent=4,
            )
            ui.alert_see_also(f"{_DOCS}/introduction/#initialisation", indent=4)
            combined_error = Exception(
                f"- dide-windows exception: {e_win}\n"
                f"- dide-linux exception: {e_linux}"
            )
            return Result.err(combined_error)
