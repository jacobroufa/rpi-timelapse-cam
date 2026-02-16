"""USB webcam backend using OpenCV.

Uses cv2.VideoCapture with CAP_V4L2 for USB webcam capture.
All cv2 imports are lazy so this module is importable on machines
without OpenCV installed.

CRITICAL: This backend is for USB webcams ONLY. OpenCV does NOT work
with Pi Camera Modules on Raspberry Pi OS Bookworm (libcamera
incompatibility -- see opencv/opencv#21653).
"""

import logging
from pathlib import Path

from timelapse.camera.base import CameraBackend

logger = logging.getLogger("timelapse.camera.usb")


class USBCameraBackend(CameraBackend):
    """Camera backend for USB webcams via OpenCV."""

    def __init__(
        self,
        device_index: int = 0,
        resolution: tuple[int, int] = (1920, 1080),
    ):
        self._device_index = device_index
        self._resolution = resolution
        self._cap = None

    @property
    def name(self) -> str:
        return "usb"

    def open(self) -> None:
        """Open the USB webcam and configure resolution."""
        import time

        import cv2

        self._cap = cv2.VideoCapture(self._device_index, cv2.CAP_V4L2)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Cannot open USB camera at device index {self._device_index}"
            )
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[0])
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[1])
        # Allow auto-exposure to settle
        time.sleep(0.5)
        logger.info(
            "USB camera opened at index %d (%dx%d)",
            self._device_index,
            self._resolution[0],
            self._resolution[1],
        )

    def capture(self, output_path: Path, quality: int = 85) -> bool:
        """Capture a JPEG frame using cv2.imwrite with IMWRITE_JPEG_QUALITY."""
        import cv2

        ret, frame = self._cap.read()
        if not ret:
            logger.error("Failed to read frame from USB camera")
            return False
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(
            str(output_path),
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), quality],
        )
        return True

    def close(self) -> None:
        """Release the capture device. Safe to call multiple times."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                logger.debug(
                    "Exception during capture release (may already be released)"
                )
            finally:
                self._cap = None

    def is_available(self) -> bool:
        """Check if a USB webcam is available at the configured device index."""
        try:
            import cv2

            cap = cv2.VideoCapture(self._device_index, cv2.CAP_V4L2)
            available = cap.isOpened()
            cap.release()
            return available
        except Exception:
            return False
