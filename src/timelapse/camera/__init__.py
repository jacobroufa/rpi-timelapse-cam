"""Camera abstraction layer.

Provides a unified interface for Pi Camera (picamera2) and USB webcam
(OpenCV) capture backends, with auto-detection and factory logic.
"""

from timelapse.camera.base import CameraBackend
from timelapse.camera.picamera import PiCameraBackend
from timelapse.camera.usb import USBCameraBackend

# detect_camera is imported after detect.py is created (Task 2).
# Use a conditional import so the package works during incremental development.
try:
    from timelapse.camera.detect import capture_with_timeout, detect_camera
except ImportError:
    pass

__all__ = [
    "CameraBackend",
    "PiCameraBackend",
    "USBCameraBackend",
    "detect_camera",
    "capture_with_timeout",
]
