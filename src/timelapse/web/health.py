"""Health data aggregation for the web UI.

Reads daemon state from .status.json and aggregates system information
for display in the base template's health indicators and the Control tab's
full system info panel.
"""

import shutil
import subprocess
from pathlib import Path

from timelapse.status import read_status


def get_health_summary(status_path: Path, config: dict) -> dict:
    """Aggregate health data for the base template's health indicators.

    Args:
        status_path: Path to the .status.json file written by the daemon.
        config: Full timelapse configuration dict.

    Returns:
        Dict with keys: daemon_state, last_capture, disk_usage_percent,
        disk_free_gb, disk_warning, captures_today, consecutive_failures,
        camera, uptime_seconds, config_loaded, capture_interval.
    """
    status = read_status(status_path) or {}
    warn_threshold = config["storage"]["warn_threshold"]
    disk_pct = status.get("disk_usage_percent", -1)

    return {
        "daemon_state": status.get("daemon", "unknown"),
        "last_capture": status.get("last_capture"),
        "disk_usage_percent": disk_pct,
        "disk_free_gb": status.get("disk_free_gb", -1),
        "disk_warning": disk_pct >= warn_threshold if disk_pct >= 0 else False,
        "captures_today": status.get("captures_today", 0),
        "consecutive_failures": status.get("consecutive_failures", 0),
        "camera": status.get("camera", "unknown"),
        "uptime_seconds": status.get("uptime_seconds", 0),
        "config_loaded": status.get("config_loaded", "unknown"),
        "capture_interval": config["capture"]["interval"],
    }


def get_full_system_info() -> dict:
    """Extended system info for hover popups and the Control tab.

    Returns:
        Dict with keys: system_uptime, disk_total_gb, disk_used_gb,
        disk_free_gb.
    """
    try:
        result = subprocess.run(
            ["uptime", "-p"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        system_uptime = result.stdout.strip()
    except Exception:
        system_uptime = "unknown"

    try:
        usage = shutil.disk_usage("/")
        disk_total_gb = round(usage.total / (1024**3), 1)
        disk_used_gb = round(usage.used / (1024**3), 1)
        disk_free_gb = round(usage.free / (1024**3), 1)
    except Exception:
        disk_total_gb = disk_used_gb = disk_free_gb = -1

    return {
        "system_uptime": system_uptime,
        "disk_total_gb": disk_total_gb,
        "disk_used_gb": disk_used_gb,
        "disk_free_gb": disk_free_gb,
    }
