"""Pi Camera backend using picamera2.

Uses picamera2 (the official Raspberry Pi camera library) for capture.
All picamera2 imports are lazy so this module is importable on machines
without picamera2 installed.

CRITICAL: Uses capture_image() + PIL Image.save(quality=N) for JPEG
quality control. capture_file() has no quality parameter.
"""

import logging
from pathlib import Path

from timelapse.camera.base import CameraBackend

logger = logging.getLogger("timelapse.camera.picamera")


class PiCameraBackend(CameraBackend):
    """Camera backend for Raspberry Pi Camera Modules via picamera2."""

    def __init__(self, resolution: tuple[int, int] = (1920, 1080)):
        self._resolution = resolution
        self._camera = None

    @property
    def name(self) -> str:
        return "picamera"

    def open(self) -> None:
        """Initialize picamera2 pipeline and allow AE/AWB to settle."""
        import time

        from picamera2 import Picamera2

        self._camera = Picamera2()
        config = self._camera.create_still_configuration(
            main={"size": self._resolution}
        )
        self._camera.configure(config)
        self._camera.start()
        # Allow auto-exposure and auto-white-balance to settle
        time.sleep(2)
        logger.info(
            "Pi Camera opened at %dx%d",
            self._resolution[0],
            self._resolution[1],
        )

    def capture(self, output_path: Path, quality: int = 85) -> bool:
        """Capture a JPEG via PIL Image for quality control.

        Uses capture_image("main") to get a PIL Image, then saves with
        the specified quality parameter. This is the only way to control
        JPEG quality with picamera2 (capture_file has no quality param).
        """
        img = self._camera.capture_image("main")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), quality=quality)
        return True

    def close(self) -> None:
        """Stop and close the camera. Safe to call multiple times."""
        if self._camera is not None:
            try:
                self._camera.stop()
                self._camera.close()
            except Exception:
                logger.debug("Exception during camera close (may already be closed)")
            finally:
                self._camera = None

    def is_available(self) -> bool:
        """Check if a Pi Camera is connected by attempting to instantiate picamera2."""
        try:
            from picamera2 import Picamera2

            cam = Picamera2()
            cam.close()
            return True
        except Exception:
            return False
