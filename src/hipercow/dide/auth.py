import getpass
import keyring
import re

from hipercow.dide.web import Credentials, DideWebClient


## Throughout this file we need to update to use a nice printing
## library, and to throw errors that the cli can nicely catch.

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
    _test_credentials(credentials)

    outro = """
Success! I'm saving these into your keyring now so that we can reuse these
when we need to log into the cluster."""
    print(outro)

    keyring.set_password("hipercow/dide/username", None, username)
    keyring.set_password("hipercow/dide/password", username, password)


def credentials() -> Credentials:
    username = keyring.get_password("hipercow/dide/username", None)
    password = keyring.get_password("hipercow/dide/password", username)
    if not username or not password:
        # The error we throw here should depend on the context; if
        # we're within click then we should point people at at
        # 'hipercow dide authenticate' but if we are being used
        # programmatically that might not be best?
        msg = ("Did not find your DIDE credentials, "
               "please run 'hipercow dide authenticate'")
        raise Exception(msg)
    return Credentials(username, password)


def check() -> None:
    print("Fetching credentials")
    creds = credentials()
    print("Testing credentials")
    _test_credentials(creds)
    print("Success!")


def clear():
    username = keyring.get_password("hipercow/dide/username", None)
    if username:
        _delete_password_silently("hipercow/dide/username", None)
        _delete_password_silently("hipercow/dide/password", username)


def _delete_password_silently(key: str, username: str | None):
    try:
        keyring.delete_password(key, username)
    except keyring.PasswordDeleteError:
        pass


def _default_username() -> str:
    return keyring.get_password("hipercow/dide/username", None) or getpass.getuser()


def _get_username(default: str) -> str:
    value = input(f"DIDE username (default: {default}) > ")
    return _check_username(value or default)


def _check_username(value) -> str:
    value = re.sub("^DIDE\\\\", "", value.strip())
    if not value:
        msg = "Invalid empty username"
        raise Exception(msg)
    if "\n" in value:
        msg = "Unexpected newline in username. Did you paste something?"
        raise Exception(msg)
    for char in " #":
        if char in value:
            msg = f"Unexpected '{char}' in username"
            raise Exception(msg)
    return value


def _get_password() -> str:
    msg = ("Please enter your DIDE password. "
           "You will not see characters while you type")
    value = getpass.getpass()
    if not value:
        msg = "Invalid empty password"
        raise Exception(msg)
    return value


def _test_credentials(credentials: Credentials):
    try:
        DideWebClient(credentials).check_access()
    except Exception as e:
        msg = "login failed"
        raise Exception(msg) from e
