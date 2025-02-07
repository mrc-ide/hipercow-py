import unittest

import keyring
import pytest

from hipercow.dide import auth


def test_strip_leading_dide_from_username():
    assert auth._check_username("DIDE\\bob") == "bob"
    assert auth._check_username("dide\\bob") == "bob"
    assert auth._check_username("bob") == "bob"
    assert auth._check_username("other\\bob") == "other\\bob"


def test_error_for_invalid_usernames():
    with pytest.raises(Exception, match="empty username"):
        auth._check_username("")
    with pytest.raises(Exception, match="Unexpected newline"):
        auth._check_username("foo\n bar")
    with pytest.raises(Exception, match="Unexpected '#'"):
        auth._check_username("username # your username here")
    with pytest.raises(Exception, match="Unexpected ' '"):
        auth._check_username("username here")


def test_can_get_password(mocker):
    mocker.patch("getpass.getpass", return_value="bob")
    assert auth._get_password() == "bob"


def test_can_error_if_given_empty_password(mocker):
    mocker.patch("getpass.getpass", return_value="")
    with pytest.raises(Exception, match="Invalid empty password"):
        assert auth._get_password()


# These would be much nicer with a fixture for temporary credentials
# (e.g., registering a backend for keyring to use within a context
# manager)
def test_authenticate_flow(mocker):
    mocker.patch("hipercow.dide.auth._default_username", return_value="bob1")
    mocker.patch("hipercow.dide.auth._get_username", return_value="bob")
    mocker.patch("hipercow.dide.auth._get_password", return_value="secret")
    mocker.patch("hipercow.dide.web.check_access", return_value="secret")
    mocker.patch("hipercow.dide.auth.check_access", return_value="secret")
    mocker.patch("keyring.set_password")
    auth.authenticate()
    assert auth._default_username.call_count == 1
    assert auth._get_username.call_count == 1
    assert auth._get_username.call_args == unittest.mock.call("bob1")
    assert auth._get_password.call_count == 1
    assert auth.check_access.call_count == 1
    assert auth.check_access.call_args == unittest.mock.call(
        auth.Credentials("bob", "secret")
    )
    assert auth.keyring.set_password.call_count == 2
    assert auth.keyring.set_password.call_args_list[0] == unittest.mock.call(
        "hipercow/dide/username", "", "bob"
    )
    assert auth.keyring.set_password.call_args_list[1] == unittest.mock.call(
        "hipercow/dide/password", "bob", "secret"
    )


def test_check_flow(mocker):
    creds = unittest.mock.Mock()
    mocker.patch("hipercow.dide.auth.fetch_credentials", return_value=creds)
    mocker.patch("hipercow.dide.auth.check_access")
    auth.check()
    assert auth.fetch_credentials.call_count == 1
    assert auth.check_access.call_count == 1
    assert auth.check_access.call_args == unittest.mock.call(creds)


def test_can_fetch_credentials_from_thekey_ring(mocker):
    mocker.patch("keyring.get_password", side_effect=["bob", "secret"])
    assert auth.fetch_credentials() == auth.Credentials("bob", "secret")
    assert auth.keyring.get_password.call_count == 2
    assert auth.keyring.get_password.call_args_list[0] == unittest.mock.call(
        "hipercow/dide/username", ""
    )
    assert auth.keyring.get_password.call_args_list[1] == unittest.mock.call(
        "hipercow/dide/password", "bob"
    )


def test_can_error_if_username_not_found(mocker):
    mocker.patch("keyring.get_password", return_value=None)
    with pytest.raises(Exception, match="Did not find your DIDE"):
        auth.fetch_credentials()


def test_can_error_if_password_not_found(mocker):
    mocker.patch("keyring.get_password", side_effect=["bob", None])
    with pytest.raises(Exception, match="Did not find your DIDE"):
        auth.fetch_credentials()


def test_can_clear_credentials(mocker):
    mocker.patch("keyring.get_password", return_value="bob")
    mocker.patch("hipercow.dide.auth._delete_password_silently")
    auth.clear()
    assert auth.keyring.get_password.call_count == 1
    assert auth._delete_password_silently.call_count == 2
    assert auth._delete_password_silently.call_args_list[
        0
    ] == unittest.mock.call("hipercow/dide/username", "")
    assert auth._delete_password_silently.call_args_list[
        1
    ] == unittest.mock.call("hipercow/dide/password", "bob")


def test_dont_clear_password_if_no_username_found(mocker):
    mocker.patch("keyring.get_password", return_value="")
    mocker.patch("hipercow.dide.auth._delete_password_silently")
    auth.clear()
    assert auth.keyring.get_password.call_count == 1
    assert auth._delete_password_silently.call_count == 0


def test_delete_password_does_not_error_if_not_found(mocker):
    mocker.patch(
        "keyring.delete_password",
        side_effect=keyring.errors.PasswordDeleteError(),
    )
    auth._delete_password_silently("foo", "bar")
    assert auth.keyring.delete_password.call_count == 1


def test_can_get_default_username(mocker):
    mocker.patch("keyring.get_password", side_effect=["", "bob"])
    mocker.patch("getpass.getuser", return_value="alice")
    assert auth._default_username() == "alice"
    assert auth.getpass.getuser.call_count == 1
    assert auth.keyring.get_password.call_count == 1
    assert auth.keyring.get_password.call_args == unittest.mock.call(
        "hipercow/dide/username", ""
    )
    assert auth._default_username() == "bob"
    assert auth.getpass.getuser.call_count == 1
    assert auth.keyring.get_password.call_count == 2


def test_can_read_username_from_input(mocker):
    mocker.patch("hipercow.dide.auth._get_input", side_effect=["", "bob"])
    assert auth._get_username("alice") == "alice"
    assert auth._get_username("alice") == "bob"
