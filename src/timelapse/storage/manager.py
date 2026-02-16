"""Storage manager: disk space checking, image path generation, output directory validation."""

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("timelapse.storage.manager")


class StorageManager:
    """Manages disk space checks, image path generation, and output directory validation.

    Args:
        output_dir: Base directory for captured images.
        stop_threshold: Disk usage percentage at which captures are refused.
        warn_threshold: Disk usage percentage at which a warning is logged.
    """

    def __init__(
        self,
        output_dir: Path,
        stop_threshold: float = 90.0,
        warn_threshold: float = 85.0,
    ):
        self._output_dir = Path(output_dir)
        self._stop_threshold = stop_threshold
        self._warn_threshold = warn_threshold

    def disk_usage_percent(self) -> float:
        """Return current disk usage as a percentage (0-100)."""
        usage = shutil.disk_usage(self._output_dir)
        return (usage.used / usage.total) * 100

    def has_space(self) -> bool:
        """Check if there is enough disk space to write a new capture.

        Returns False if usage is at or above the stop threshold.
        Logs a warning if usage is at or above the warn threshold but below stop.
        Returns True otherwise.
        """
        percent = self.disk_usage_percent()
        if percent >= self._stop_threshold:
            logger.error(
                "Disk usage at %.1f%% -- at or above stop threshold (%.1f%%), "
                "refusing to write",
                percent,
                self._stop_threshold,
            )
            return False
        if percent >= self._warn_threshold:
            logger.warning(
                "Disk usage at %.1f%%, approaching limit (%.1f%%)",
                percent,
                self._warn_threshold,
            )
        return True

    def image_path(self, timestamp: datetime) -> Path:
        """Generate the full path for an image based on a timestamp.

        Path format: output_dir/YYYY/MM/DD/HHMMSS.jpg
        Creates parent directories if they do not exist.

        Args:
            timestamp: The datetime to derive the path from.

        Returns:
            Full Path to the image file.
        """
        path = (
            self._output_dir
            / timestamp.strftime("%Y")
            / timestamp.strftime("%m")
            / timestamp.strftime("%d")
            / f"{timestamp.strftime('%H%M%S')}.jpg"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def ensure_output_dir(self) -> None:
        """Validate that the output directory exists and is writable.

        Creates the directory if it does not exist. Raises SystemExit if the
        directory cannot be created or is not writable.
        """
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SystemExit(
                f"Cannot create output directory {self._output_dir}: {exc}"
            )

        # Check writability by attempting to create a temporary file
        test_file = self._output_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except OSError as exc:
            raise SystemExit(
                f"Output directory {self._output_dir} is not writable: {exc}"
            )

        logger.info("Output directory ready: %s", self._output_dir)
