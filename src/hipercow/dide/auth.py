import getpass
import re

import keyring

from hipercow import ui
from hipercow.dide.web import Credentials, check_access

## We follow hipercow in storing the username *as* a password, because
## it's largely a computer-specific things.


def authenticate():
    ui.h1("Please enter your DIDE credentials")
    ui.text(
        """
We need to know your DIDE username and password in order to log you into
the cluster. This will be shared across all projects on this machine, with
the username and password stored securely in your system keychain. You will
have to run this command again on other computers."""
    )

    ui.text(
        """
Your DIDE password may differ from your Imperial password, and in some
cases your username may also differ. If in doubt, perhaps try logging in
at https://mrcdata.dide.ic.ac.uk/hpc" and use the combination that works
for you there."""
    )

    ui.text(
        """
If you are unsure, please see our documentation about passwords:
https://mrc-ide.github.io/hipercow-py/dide/#about-our-usernames-and-passwords\
"""
    )

    ui.blank_line()
    username = _get_username(_default_username())

    ui.alert_info(f"Using username '{username}'")

    ui.blank_line()
    password = _get_password()

    ui.text(
        """
I am going to to try and log in with your password now.
If this fails we can always try again."""
    )

    credentials = Credentials(username, password)
    check_access(credentials)

    ui.blank_line()
    ui.alert_success("Username and password are correct")
    ui.alert_info("I am saving these into your keyring now")
    ui.alert_info(
        "You can delete your credentials with "
        "'hipercow dide authenticate clear'"
    )

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
    ui.alert_info("Fetching credentials")
    credentials = fetch_credentials()
    ui.alert_info("Testing credentials")
    check_access(credentials)
    ui.alert_info("Success!")


def clear():
    username = keyring.get_password("hipercow/dide/username", "")
    if username:
        ui.alert_warning(f"Deleting credentials for '{username}'")
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
    # I did look at the rich.prompt.Prompt() way of doing this but it
    # does not seem to add much:
    #
    #   value = Prompt.ask("DIDE username", default=default)
    #
    # with a similar implementation for the password case.
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
        "You will not see characters while you type."
    )
    ui.text(msg)
    value = getpass.getpass()
    if not value:
        msg = "Invalid empty password"
        raise Exception(msg)
    return value
