"""Camera auto-detection and capture timeout wrapper.

Provides a factory function that selects the appropriate camera backend
based on configuration (auto, picamera, usb) and a timeout wrapper
to prevent capture hangs.
"""

import logging
import threading
from pathlib import Path

from timelapse.camera.base import CameraBackend
from timelapse.camera.picamera import PiCameraBackend
from timelapse.camera.usb import USBCameraBackend

logger = logging.getLogger("timelapse.camera.detect")


def detect_camera(config: dict) -> CameraBackend:
    """Detect and instantiate the appropriate camera backend.

    Args:
        config: Application configuration dict. Reads:
            - config["capture"]["source"]: "auto", "picamera", or "usb"
            - config["capture"]["resolution"]: [width, height]
            - config["capture"]["device_index"]: USB device index (optional, default 0)

    Returns:
        An instance of CameraBackend (not yet opened).

    Raises:
        RuntimeError: If the requested camera is not available.
    """
    capture_cfg = config.get("capture", {})
    source = capture_cfg.get("source", "auto")
    resolution_list = capture_cfg.get("resolution", [1920, 1080])
    resolution = (resolution_list[0], resolution_list[1])
    device_index = capture_cfg.get("device_index", 0)

    if source == "picamera":
        backend = PiCameraBackend(resolution=resolution)
        if not backend.is_available():
            raise RuntimeError(
                "Pi Camera source requested but picamera2 is not available. "
                "Ensure a Pi Camera Module is connected and picamera2 is installed."
            )
        logger.info("Camera selected: picamera (forced)")
        return backend

    if source == "usb":
        backend = USBCameraBackend(
            device_index=device_index, resolution=resolution
        )
        if not backend.is_available():
            raise RuntimeError(
                f"USB camera source requested but no camera found at device index "
                f"{device_index}. Ensure a USB webcam is connected."
            )
        logger.info("Camera selected: usb (forced)")
        return backend

    # Auto-detection: try picamera2 first, then USB
    pi_backend = PiCameraBackend(resolution=resolution)
    if pi_backend.is_available():
        logger.info("Camera selected: picamera (auto-detected)")
        return pi_backend

    usb_backend = USBCameraBackend(
        device_index=device_index, resolution=resolution
    )
    if usb_backend.is_available():
        logger.info("Camera selected: usb (auto-detected)")
        return usb_backend

    raise RuntimeError(
        "No camera detected. Auto-detection tried:\n"
        "  1. Pi Camera (picamera2) -- not available\n"
        "  2. USB webcam (OpenCV) at device index 0 -- not available\n"
        "Ensure a camera is connected and the appropriate library is installed."
    )


def capture_with_timeout(
    camera: CameraBackend,
    output_path: Path,
    quality: int = 85,
    timeout: int = 30,
) -> bool:
    """Run a capture with a timeout to prevent hangs.

    Executes camera.capture() in a separate thread and joins with the
    specified timeout. If the capture does not complete within the
    timeout period, returns False.

    Args:
        camera: An opened CameraBackend instance.
        output_path: Full path for the output JPEG file.
        quality: JPEG quality (1-100).
        timeout: Maximum seconds to wait for capture. Default 30.

    Returns:
        True if capture succeeded within timeout, False otherwise.
    """
    result = [False]
    exception = [None]

    def _do_capture():
        try:
            result[0] = camera.capture(output_path, quality)
        except Exception as exc:
            exception[0] = exc

    thread = threading.Thread(target=_do_capture, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        logger.error(
            "Capture timed out after %d seconds for %s", timeout, output_path
        )
        return False

    if exception[0] is not None:
        logger.error("Capture raised exception: %s", exception[0])
        return False

    return result[0]
