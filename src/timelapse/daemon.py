"""Main capture daemon loop with signal handling and error recovery.

Ties together the config, camera, storage, and status subsystems into a
running daemon that captures images at a configurable interval, checks
disk space, runs cleanup, and recovers from camera disconnects.
"""

import logging
import random
import signal
import time
from datetime import datetime
from pathlib import Path

from timelapse.camera.detect import capture_with_timeout, detect_camera
from timelapse.config import load_config
from timelapse.lock import camera_lock
from timelapse.status import write_status
from timelapse.storage import StorageManager, cleanup_old_days

logger = logging.getLogger("timelapse.daemon")

# Config keys that require a restart to take effect
_NO_RELOAD_KEYS = {"source", "resolution", "output_dir"}


class CaptureDaemon:
    """Capture daemon that runs the main loop.

    Args:
        config: Application configuration dict (from load_config).
        config_path: Path to the YAML config file (for SIGHUP reload).
    """

    def __init__(self, config: dict, config_path: Path):
        self._config = config
        self._config_path = config_path
        self._running = False

        # State tracking
        self._consecutive_failures = 0
        self._captures_today = 0
        self._captures_today_date = datetime.now().date()
        self._start_time = time.monotonic()

        # Initialize subsystems
        self._camera = detect_camera(config)
        storage_cfg = config["storage"]
        self._storage = StorageManager(
            output_dir=Path(storage_cfg["output_dir"]),
            stop_threshold=storage_cfg["stop_threshold"],
            warn_threshold=storage_cfg["warn_threshold"],
        )

        # Status file location: inside the output directory
        self._status_path = Path(storage_cfg["output_dir"]) / ".status.json"

        # Last capture timestamp for status reporting
        self._last_capture: str | None = None
        self._last_capture_success: bool | None = None

    def run(self) -> None:
        """Run the main capture loop.

        Registers signal handlers, opens the camera, and enters the
        capture loop. Runs until SIGTERM or SIGINT is received.
        """
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGHUP, self._handle_reload)

        self._running = True
        self._start_time = time.monotonic()

        try:
            self._camera.open()
            logger.info(
                "Camera opened (%s), starting capture loop", self._camera.name
            )

            while self._running:
                loop_start = time.monotonic()

                # Reset daily counter at midnight
                today = datetime.now().date()
                if today != self._captures_today_date:
                    self._captures_today = 0
                    self._captures_today_date = today

                self._capture_once()
                self._write_status("running")

                # Drift-corrected sleep
                elapsed = time.monotonic() - loop_start
                interval = self._config["capture"]["interval"]
                sleep_time = max(0, interval - elapsed)

                # Sleep in small increments to allow quick shutdown
                sleep_end = time.monotonic() + sleep_time
                while self._running and time.monotonic() < sleep_end:
                    remaining = sleep_end - time.monotonic()
                    time.sleep(min(0.5, remaining))

        except Exception as exc:
            logger.error("Fatal error in capture loop: %s", exc)
            self._write_status("error")
            raise
        finally:
            try:
                self._camera.close()
            except Exception as exc:
                logger.warning("Error closing camera: %s", exc)
            self._write_status("stopped")
            logger.info("Daemon stopped")

    def _capture_once(self) -> None:
        """Execute a single capture cycle.

        Checks disk space, generates the output path, acquires the camera
        lock, captures the image, and optionally runs cleanup.
        """
        # Check disk space before capturing
        if not self._storage.has_space():
            logger.error(
                "Disk usage exceeds %d%% threshold, skipping capture",
                self._config["storage"]["stop_threshold"],
            )
            return

        now = datetime.now()
        output_path = self._storage.image_path(now)

        # Check for filename collision (same-second capture)
        if output_path.exists():
            logger.debug(
                "Image already exists at %s, skipping duplicate", output_path
            )
            return

        try:
            with camera_lock(blocking=True):
                success = capture_with_timeout(
                    self._camera,
                    output_path,
                    quality=self._config["capture"]["jpeg_quality"],
                    timeout=30,
                )

            self._last_capture = now.isoformat()

            if success:
                self._consecutive_failures = 0
                self._captures_today += 1
                self._last_capture_success = True

                if self._config["logging"].get("gap_tracking", False):
                    logger.info("Capture saved: %s", output_path)
            else:
                self._handle_capture_failure("Capture returned False")

        except Exception as exc:
            logger.error("Capture error: %s", exc)
            self._handle_capture_failure(str(exc))

        # Run cleanup if enabled
        if self._config["storage"].get("cleanup_enabled", False):
            try:
                output_dir = Path(self._config["storage"]["output_dir"])
                retention = self._config["storage"]["retention_days"]
                deleted = cleanup_old_days(output_dir, retention)
                if deleted > 0:
                    logger.info("Cleanup removed %d old day directories", deleted)
            except Exception as exc:
                logger.error("Cleanup error: %s", exc)

    def _handle_capture_failure(self, reason: str) -> None:
        """Handle a capture failure with exponential backoff recovery.

        Increments the failure counter, calculates a backoff delay, and
        attempts to reopen the camera.

        Args:
            reason: Description of the failure for logging.
        """
        self._consecutive_failures += 1
        self._last_capture_success = False

        # Exponential backoff: 5s base, 300s max, with jitter
        backoff = min(
            5 * (2 ** self._consecutive_failures) + random.uniform(0, 1),
            300,
        )

        logger.warning(
            "Capture failed (attempt %d): %s -- backing off %.1fs",
            self._consecutive_failures,
            reason,
            backoff,
        )

        # Attempt camera recovery
        try:
            self._camera.close()
        except Exception:
            pass

        # Sleep for backoff period (interruptible)
        sleep_end = time.monotonic() + backoff
        while self._running and time.monotonic() < sleep_end:
            remaining = sleep_end - time.monotonic()
            time.sleep(min(0.5, remaining))

        if not self._running:
            return

        # Attempt to reopen camera
        try:
            self._camera.open()
            logger.info(
                "Camera reconnected (%s) after %d failures",
                self._camera.name,
                self._consecutive_failures,
            )
        except Exception as exc:
            logger.error("Camera reconnect failed: %s", exc)

    def _handle_shutdown(self, signum, frame) -> None:
        """Handle SIGTERM/SIGINT for graceful shutdown."""
        sig_name = signal.Signals(signum).name
        logger.info("Received %s, shutting down gracefully", sig_name)
        self._running = False

    def _handle_reload(self, signum, frame) -> None:
        """Handle SIGHUP for configuration reload.

        Reloads the config file and updates runtime settings. Settings
        that require a restart (source, resolution, output_dir) log a
        warning if changed but are not applied.
        """
        logger.info("SIGHUP received, reloading configuration")
        try:
            new_config = load_config(self._config_path)
        except (SystemExit, Exception) as exc:
            logger.error("Config reload failed, keeping current config: %s", exc)
            return

        # Warn about settings that require a restart
        for key in _NO_RELOAD_KEYS:
            old_val = self._config.get("capture", {}).get(
                key, self._config.get("storage", {}).get(key)
            )
            new_val = new_config.get("capture", {}).get(
                key, new_config.get("storage", {}).get(key)
            )
            if old_val != new_val:
                logger.warning(
                    "Config key '%s' changed (%s -> %s) but requires daemon "
                    "restart to take effect",
                    key,
                    old_val,
                    new_val,
                )

        # Apply reloadable settings
        self._config = new_config

        # Update storage manager thresholds
        storage_cfg = new_config["storage"]
        self._storage._stop_threshold = storage_cfg["stop_threshold"]
        self._storage._warn_threshold = storage_cfg["warn_threshold"]

        logger.info("Configuration reloaded successfully")

    def _write_status(self, daemon_state: str) -> None:
        """Write the current daemon status to the JSON status file.

        Args:
            daemon_state: Current daemon state (running, stopped, error).
        """
        uptime = time.monotonic() - self._start_time
        try:
            disk_percent = self._storage.disk_usage_percent()
            import shutil

            usage = shutil.disk_usage(self._config["storage"]["output_dir"])
            disk_free_gb = round(usage.free / (1024**3), 2)
        except Exception:
            disk_percent = -1
            disk_free_gb = -1

        data = {
            "daemon": daemon_state,
            "camera": self._camera.name if self._camera else "unknown",
            "last_capture": self._last_capture,
            "last_capture_success": self._last_capture_success,
            "consecutive_failures": self._consecutive_failures,
            "captures_today": self._captures_today,
            "disk_usage_percent": round(disk_percent, 1),
            "disk_free_gb": disk_free_gb,
            "uptime_seconds": round(uptime, 1),
            "config_loaded": str(self._config_path),
        }

        try:
            write_status(self._status_path, data)
        except Exception as exc:
            logger.warning("Failed to write status file: %s", exc)
