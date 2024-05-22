"""Zino API authentication mechanisms.

This only implements the authentication scheme of the legacy server protocol.
"""

import io
import secrets
from hashlib import sha1
from pathlib import Path
from typing import Optional, Union


def authenticate(
    user: str, response: str, challenge: Optional[str] = None, secrets_file: Optional[Union[Path, str]] = "secrets"
) -> bool:
    """Authenticates a user challenge response.

    An unsuccessful authentication will raise an AuthenticationFailure, otherwise True is returned.

    As per the original Zino specification, a newly connected user will be issued a challenge string, and must prove
    they know the user's secret by responding to the challenge with something that corresponds to
    `SHA1(challenge + " " + secret)`
    """
    users = read_users(secrets_file)
    if user not in users:
        raise AuthenticationFailure("no such user")

    if not challenge:
        # We do not support other authentication modes yet
        raise AuthenticationFailure("only challenge-response authentication is supported right now")

    cleartext = f"{challenge} {users[user]}".encode()
    expected = sha1(cleartext).hexdigest()
    if response == expected:
        return True
    else:
        raise AuthenticationFailure()
        # The original Zino code also supports fallback to cleartext and tacacs authentication, but only if enabled


def get_challenge() -> str:
    """Returns a new authentication challenge string"""
    # The original Zino codebase uses a SHA1 hash of the current timestamp, but this is too predictable, so we use more
    # randomness
    string = secrets.token_bytes(40)
    return sha1(string).hexdigest()


def read_users(filename: Optional[Union[Path, str]] = "secrets") -> dict[str, str]:
    """Reads the legacy users database and returns a dictionary of usernames and their secrets"""
    secrets = {}
    with io.open(filename, "r", encoding="utf-8") as users:
        nonempty_lines = (ln.strip() for ln in users.readlines() if ln.strip())
        for line in nonempty_lines:
            user, secret = line.split(" ", maxsplit=1)
            secrets[user] = secret

    return secrets


class AuthenticationFailure(Exception):
    def __init__(self, message="Authentication failure"):
        super().__init__(message)
