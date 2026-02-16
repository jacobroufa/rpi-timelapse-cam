"""Abstract camera backend interface."""

from abc import ABC, abstractmethod
from pathlib import Path


class CameraBackend(ABC):
    """Abstract interface for camera capture backends.

    Subclasses must implement open, capture, close, and is_available.
    The camera pipeline should be kept open between captures for minimal
    latency and stable auto-exposure.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name for logging."""
        ...

    @abstractmethod
    def open(self) -> None:
        """Initialize and start the camera pipeline.

        Keep the pipeline open for reuse between captures.
        """
        ...

    @abstractmethod
    def capture(self, output_path: Path, quality: int = 85) -> bool:
        """Capture a single JPEG image.

        Args:
            output_path: Full path for the output JPEG file.
                Parent directories will be created if needed.
            quality: JPEG quality (1-100). Default 85.

        Returns:
            True on success, False on failure.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Release camera resources.

        Must be safe to call multiple times (guard against double-close).
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this camera type is currently connected and available.

        Returns:
            True if the camera hardware is accessible.
        """
        ...
