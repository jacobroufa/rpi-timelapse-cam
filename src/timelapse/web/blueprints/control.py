"""Control tab blueprint.

Provides PAM-authenticated daemon start/stop controls and full system
health display. All routes require HTTP Basic Auth verified against
Linux PAM credentials.
"""

import logging
import subprocess

from flask import Blueprint, current_app, jsonify, render_template

from timelapse.web.auth import auth
from timelapse.web.health import get_full_system_info

logger = logging.getLogger(__name__)

control_bp = Blueprint("control", __name__)

SERVICE_NAME = "timelapse-capture"
SYSTEMCTL_PATH = "/usr/bin/systemctl"


def _get_service_status() -> str:
    """Check if the capture service is running.

    Returns:
        Service state string: 'active', 'inactive', 'failed', or 'unknown'.
    """
    try:
        result = subprocess.run(
            ["sudo", SYSTEMCTL_PATH, "is-active", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() or "unknown"
    except subprocess.TimeoutExpired:
        logger.error("Timeout checking service status")
        return "unknown"
    except Exception:
        logger.exception("Error checking service status")
        return "unknown"


def _start_service() -> tuple[bool, str]:
    """Start the capture service.

    Returns:
        Tuple of (success, message).
    """
    try:
        result = subprocess.run(
            ["sudo", SYSTEMCTL_PATH, "start", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, "Service started"
        return False, result.stderr.strip() or "Failed to start service"
    except subprocess.TimeoutExpired:
        return False, "Timeout starting service"
    except Exception as e:
        return False, str(e)


def _stop_service() -> tuple[bool, str]:
    """Stop the capture service.

    Returns:
        Tuple of (success, message).
    """
    try:
        result = subprocess.run(
            ["sudo", SYSTEMCTL_PATH, "stop", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, "Service stopped"
        return False, result.stderr.strip() or "Failed to stop service"
    except subprocess.TimeoutExpired:
        return False, "Timeout stopping service"
    except Exception as e:
        return False, str(e)


def _get_config_summary(config: dict) -> dict:
    """Extract relevant config values for display.

    Args:
        config: Full timelapse configuration dict.

    Returns:
        Dict with user-facing config summary.
    """
    capture = config.get("capture", {})
    storage = config.get("storage", {})
    cleanup = config.get("cleanup", {})

    return {
        "interval": capture.get("interval", "unknown"),
        "quality": capture.get("quality", "unknown"),
        "source": capture.get("source", "unknown"),
        "output_dir": storage.get("output_dir", "unknown"),
        "warn_threshold": storage.get("warn_threshold", "unknown"),
        "stop_threshold": storage.get("stop_threshold", "unknown"),
        "cleanup_enabled": cleanup.get("enabled", False),
        "retention_days": cleanup.get("retention_days", "N/A"),
    }


@control_bp.route("/")
@auth.login_required
def index():
    """Render the Control tab with daemon controls and system health."""
    config = current_app.config["TIMELAPSE"]

    return render_template(
        "control.html",
        service_status=_get_service_status(),
        system_info=get_full_system_info(),
        config_summary=_get_config_summary(config),
        user=auth.current_user(),
    )


@control_bp.route("/start", methods=["POST"])
@auth.login_required
def start():
    """Start the capture daemon. Returns JSON response."""
    success, message = _start_service()
    status = _get_service_status()
    return jsonify({"success": success, "status": status, "message": message})


@control_bp.route("/stop", methods=["POST"])
@auth.login_required
def stop():
    """Stop the capture daemon. Returns JSON response."""
    success, message = _stop_service()
    status = _get_service_status()
    return jsonify({"success": success, "status": status, "message": message})


@control_bp.route("/status")
@auth.login_required
def status():
    """Return current service status and health data as JSON."""
    config = current_app.config["TIMELAPSE"]
    status_file = current_app.config["STATUS_FILE"]

    from timelapse.web.health import get_health_summary

    return jsonify(
        {
            "service_status": _get_service_status(),
            "health": get_health_summary(status_file, config),
            "system_info": get_full_system_info(),
        }
    )
