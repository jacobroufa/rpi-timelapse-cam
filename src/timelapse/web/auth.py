"""PAM authentication wrapper for Flask-HTTPAuth.

Provides HTTP Basic Auth backed by Linux PAM credentials. Used by the
Control tab blueprint to gate access to daemon management and system
health information.
"""

import logging

import pam
from flask_httpauth import HTTPBasicAuth

logger = logging.getLogger(__name__)

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username: str, password: str) -> str | None:
    """Verify credentials against the Linux PAM stack.

    Args:
        username: Linux system username.
        password: Linux system password.

    Returns:
        The username on success, None on failure.
    """
    if not username or not password:
        return None

    p = pam.pam()
    if p.authenticate(username, password):
        return username

    logger.warning("Authentication failed for user: %s", username)
    return None
