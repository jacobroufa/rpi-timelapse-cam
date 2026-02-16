"""Atomic JSON status file writer and reader.

Provides functions to write and read a JSON status file used to communicate
daemon state to the web UI (Phase 2). Writes are atomic: data is written to
a temporary file in the same directory, then renamed to the target path.
This prevents readers from seeing a partially-written file.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("timelapse.status")


def write_status(status_path: Path, data: dict) -> None:
    """Write status data to a JSON file atomically.

    Writes to a temporary file in the same directory as status_path, then
    renames it to the target path. This ensures readers never see a
    partially-written file.

    Args:
        status_path: Path to the status JSON file.
        data: Dictionary of status data. Expected keys:
            daemon, camera, last_capture, last_capture_success,
            consecutive_failures, captures_today, disk_usage_percent,
            disk_free_gb, uptime_seconds, config_loaded
    """
    status_path = Path(status_path)
    status_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temp file in the same directory, then rename for atomicity
    fd, tmp_path = tempfile.mkstemp(
        dir=status_path.parent, suffix=".tmp", prefix=".status-"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.rename(tmp_path, status_path)
        logger.debug("Status file written: %s", status_path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_status(status_path: Path) -> dict | None:
    """Read status data from a JSON file.

    Args:
        status_path: Path to the status JSON file.

    Returns:
        A dict of status data, or None if the file does not exist or
        cannot be parsed.
    """
    status_path = Path(status_path)
    if not status_path.exists():
        return None

    try:
        with open(status_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read status file %s: %s", status_path, exc)
        return None
