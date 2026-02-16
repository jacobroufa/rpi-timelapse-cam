"""File-based camera mutex using fcntl.flock.

Provides a context manager that acquires an exclusive lock on a lock file
to prevent simultaneous camera access between the capture daemon and the
web server (Phase 2).
"""

import fcntl
import logging
import os
from contextlib import contextmanager

logger = logging.getLogger("timelapse.lock")


@contextmanager
def camera_lock(lock_path: str = "/tmp/timelapse-camera.lock", blocking: bool = True):
    """Acquire an exclusive camera lock.

    Uses fcntl.flock for inter-process mutual exclusion. The lock is
    automatically released when the context manager exits or the process
    dies (OS-managed).

    Args:
        lock_path: Path to the lock file. Default: /tmp/timelapse-camera.lock
        blocking: If True, wait for the lock. If False, raise
            BlockingIOError immediately if the lock is held by another
            process. Non-blocking mode is intended for the web server
            live view (Phase 2).

    Yields:
        None

    Raises:
        BlockingIOError: If blocking=False and the lock is already held.
    """
    lock_file = open(lock_path, "w")
    try:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        fcntl.flock(lock_file, flags)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        logger.debug("Camera lock acquired (pid=%d)", os.getpid())
        yield
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
        logger.debug("Camera lock released (pid=%d)", os.getpid())
