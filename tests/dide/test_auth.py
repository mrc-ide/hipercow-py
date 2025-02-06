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
