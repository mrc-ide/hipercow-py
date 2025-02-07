import getpass
import re

import keyring

from hipercow.dide.web import Credentials, check_access

## Throughout this file we need to update to use a nice printing
## library, and to throw errors that the cli can nicely catch.

## We follow hipercow in storing the username *as* a password, because
## it's largely a computer-specific things.


def authenticate():
    intro = """# Please enter your DIDE credentials

We need to know your DIDE username and password in order to log you into
the cluster. This will be shared across all projects on this machine, with
the username and password stored securely in your system keychain. You will
have to run this command again on other computers

Your DIDE password may differ from your Imperial password, and in some
cases your username may also differ. If in doubt, perhaps try logging in
at https://mrcdata.dide.ic.ac.uk/hpc" and use the combination that works
for you there.
"""
    print(intro)

    username = _get_username(_default_username())

    print(f"Using username '{username}'\n")

    password = _get_password()

    check = """I am going to to try and log in with your password now.
If this fails we can always try again"""
    print(check)

    credentials = Credentials(username, password)
    check_access(credentials)

    outro = """
Success! I'm saving these into your keyring now so that we can reuse these
when we need to log into the cluster."""
    print(outro)

    keyring.set_password("hipercow/dide/username", "", username)
    keyring.set_password("hipercow/dide/password", username, password)


def fetch_credentials() -> Credentials:
    username = keyring.get_password("hipercow/dide/username", "") or ""
    password = keyring.get_password("hipercow/dide/password", username)
    if not username or not password:
        # The error we throw here should depend on the context; if
        # we're within click then we should point people at at
        # 'hipercow dide authenticate' but if we are being used
        # programmatically that might not be best?
        msg = (
            "Did not find your DIDE credentials, "
            "please run 'hipercow dide authenticate'"
        )
        raise Exception(msg)
    return Credentials(username, password)


def check() -> None:
    print("Fetching credentials")
    credentials = fetch_credentials()
    print("Testing credentials")
    check_access(credentials)
    print("Success!")


def clear():
    username = keyring.get_password("hipercow/dide/username", "")
    if username:
        _delete_password_silently("hipercow/dide/username", "")
        _delete_password_silently("hipercow/dide/password", username)


def _delete_password_silently(key: str, username: str):
    try:
        keyring.delete_password(key, username)
    except keyring.errors.PasswordDeleteError:
        pass


def _default_username() -> str:
    return (
        keyring.get_password("hipercow/dide/username", "") or getpass.getuser()
    )


# For mocking to work
def _get_input(text):
    return input(text)  # pragma: no cover


def _get_username(default: str) -> str:
    value = _get_input(f"DIDE username (default: {default}) > ")
    return _check_username(value or default)


def _check_username(value) -> str:
    value = re.sub("^DIDE\\\\", "", value.strip(), flags=re.IGNORECASE)
    if not value:
        msg = "Invalid empty username"
        raise Exception(msg)
    if "\n" in value:
        msg = "Unexpected newline in username. Did you paste something?"
        raise Exception(msg)
    for char in "# ":
        if char in value:
            msg = f"Unexpected '{char}' in username"
            raise Exception(msg)
    return value


def _get_password() -> str:
    msg = (
        "Please enter your DIDE password. "
        "You will not see characters while you type"
    )
    value = getpass.getpass()
    if not value:
        msg = "Invalid empty password"
        raise Exception(msg)
    return value
