from pathlib import Path
from unittest import mock

import pytest

import hipercow.dide.check
from hipercow import root
from hipercow.dide.auth import Credentials
from hipercow.dide.check import (
    _dide_check_connection,
    _dide_check_credentials,
    _dide_check_path,
    _dide_check_root,
    _dide_check_root_configured,
    dide_check,
)
from hipercow.util import Result


def test_user_facing_check_function_success(mocker, capsys):
    ok = Result.ok()
    mocker.patch("hipercow.dide.check._dide_check_credentials", return_value=ok)
    mocker.patch("hipercow.dide.check._dide_check_connection", return_value=ok)
    mocker.patch("hipercow.dide.check._dide_check_path", return_value=ok)
    mocker.patch("hipercow.dide.check._dide_check_root", return_value=ok)
    dide_check(Path.cwd())
    out = capsys.readouterr().out
    assert "You look good to go!" in out


def test_user_facing_check_function_failure(mocker):
    ok = Result.ok()
    err = Result.err(Exception("foo"))
    mocker.patch("hipercow.dide.check._dide_check_credentials", return_value=ok)
    mocker.patch("hipercow.dide.check._dide_check_connection", return_value=ok)
    mocker.patch("hipercow.dide.check._dide_check_path", return_value=err)
    mocker.patch("hipercow.dide.check._dide_check_root", return_value=ok)
    with pytest.raises(Exception, match="You have issues to address"):
        dide_check()


def test_user_facing_check_function_config_failure(mocker):
    ok = Result.ok()
    err = Result.err(Exception("foo"))
    mocker.patch("hipercow.dide.check._dide_check_credentials", return_value=ok)
    mocker.patch("hipercow.dide.check._dide_check_connection", return_value=ok)
    mocker.patch("hipercow.dide.check._dide_check_path", return_value=ok)
    mocker.patch("hipercow.dide.check._dide_check_root", return_value=err)
    with pytest.raises(Exception, match="You have issues to address"):
        dide_check()


def test_successful_credentials_read(mocker, capsys):
    creds = Credentials("bob", "password")
    mocker.patch("hipercow.dide.check.fetch_credentials", return_value=creds)
    mocker.patch("hipercow.dide.check.check_access")
    res = _dide_check_credentials()
    assert res

    out = capsys.readouterr().out
    assert "Checking DIDE credentials" in out
    assert "Found DIDE credentials" in out
    assert "Your username is 'bob'" in out
    assert "DIDE credentials are correct" in out


def test_error_if_no_credentials_found(mocker, capsys):
    mocker.patch(
        "hipercow.dide.check.fetch_credentials",
        side_effect=Exception("no creds"),
    )
    mocker.patch("hipercow.dide.check.check_access")
    res = _dide_check_credentials()
    assert not res

    out = capsys.readouterr().out
    assert "no creds\n" in out

    assert hipercow.dide.check.fetch_credentials.call_count == 1
    assert hipercow.dide.check.check_access.call_count == 0


def test_error_if_credentials_fail(mocker, capsys):
    creds = Credentials("bob", "password")
    mocker.patch("hipercow.dide.check.fetch_credentials", return_value=creds)
    mocker.patch(
        "hipercow.dide.check.check_access", side_effect=Exception("no access")
    )
    res = _dide_check_credentials()
    assert not res

    out = capsys.readouterr().out
    assert "no access\n" in out

    assert hipercow.dide.check.fetch_credentials.call_count == 1
    assert hipercow.dide.check.check_access.call_count == 1


def test_successful_connection_test(mocker, capsys):
    mocker.patch("hipercow.dide.check.requests")
    assert _dide_check_connection()

    out = capsys.readouterr().out
    assert "Connection to private network is working" in out


def test_failed_connection_test(mocker, capsys):
    mocker.patch(
        "hipercow.dide.check.requests.head",
        side_effect=Exception("no internet"),
    )
    assert not _dide_check_connection()
    out = capsys.readouterr().out
    assert "Failed to make connection to the private network" in out


def test_successful_path_mapping(mocker, capsys):
    mocker.patch("hipercow.dide.check.detect_mounts")
    mocker.patch("hipercow.dide.check.remap_path")
    assert _dide_check_path(Path.cwd())

    out = capsys.readouterr().out
    assert "Path looks like it is on a network share" in out


def test_failed_path_mapping(mocker, capsys):
    mocker.patch("hipercow.dide.check.detect_mounts")
    mocker.patch(
        "hipercow.dide.check.remap_path", side_effect=Exception("wrong path")
    )
    assert not _dide_check_path(Path.cwd())

    out = capsys.readouterr().out
    assert "Failed to map path to a network share" in out


def test_successful_initialisation(tmp_path, capsys, mocker):
    mock_check_configured = mocker.Mock()
    mocker.patch(
        "hipercow.dide.check._dide_check_root_configured", mock_check_configured
    )
    root.init(tmp_path)
    capsys.readouterr()
    assert _dide_check_root(tmp_path)
    out = capsys.readouterr().out
    assert "hipercow is initialised at" in out
    assert mock_check_configured.call_count == 1


def test_unsuccessful_initialisation(tmp_path, capsys):
    assert not _dide_check_root(tmp_path)
    out = capsys.readouterr().out
    assert "hipercow is not initialised" in out


def test_can_test_that_dide_windows_is_configured(capsys, mocker):
    mock_load_driver = mocker.Mock()
    mocker.patch("hipercow.dide.check.load_driver", mock_load_driver)
    root = mock.Mock()
    assert _dide_check_root_configured(root)
    out = capsys.readouterr().out
    assert "hipercow is configured to use 'dide-windows'" in out
    assert mock_load_driver.call_count == 1
    assert mock_load_driver.mock_calls[0] == mock.call("dide-windows", root)


def test_can_report_that_dide_windows_is_not_configured(capsys, mocker):
    mocker.patch(
        "hipercow.dide.check.load_driver",
        side_effect=Exception("not configured"),
    )
    root = mock.Mock()
    assert not _dide_check_root_configured(root)
    out = capsys.readouterr().out
    assert "hipercow is not configured with a valid driver" in out
