from dataclasses import dataclass
import keychain


@dataclass
class Credentials:
    username: str
    password: str


def dide_authenticate():
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
