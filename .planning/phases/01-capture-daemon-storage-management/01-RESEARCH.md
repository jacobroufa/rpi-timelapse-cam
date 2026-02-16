# Phase 1: Capture Daemon & Storage Management - Research

**Researched:** 2026-02-16
**Domain:** Python camera capture daemon on Raspberry Pi (picamera2, OpenCV, systemd)
**Confidence:** HIGH

## Summary

Phase 1 builds a background daemon that captures images from a Pi Camera or USB webcam at a configurable interval, saves them to date-organized directories, manages disk space, and runs as a systemd service. The technical landscape is well-understood: picamera2 (0.3.33+) is the only viable option for Pi Camera capture on modern Raspberry Pi OS, while OpenCV's VideoCapture handles USB webcams exclusively. A critical finding is that `cv2.VideoCapture(0)` does NOT work with Pi Camera Modules on Bookworm -- the libcamera stack is incompatible with OpenCV's V4L2 backend. This means the camera abstraction layer must use two genuinely different backends, not two paths into the same library.

The daemon architecture is straightforward: a long-running Python process with a sleep loop, managed by systemd, that keeps the camera pipeline open between captures for minimal latency. JPEG quality control requires different mechanisms per backend (PIL's `Image.save(quality=N)` for picamera2, `cv2.imwrite` with `IMWRITE_JPEG_QUALITY` for OpenCV). Storage management uses stdlib's `shutil.disk_usage()` with a pre-capture check, and cleanup deletes oldest full day directories. Configuration is a single YAML file loaded with `PyYAML.safe_load()`.

**Primary recommendation:** Build a camera abstraction with two backends (PiCameraBackend using picamera2, USBCameraBackend using OpenCV), a main capture loop that keeps the camera open and uses `time.sleep()` for intervals, a storage manager module for disk checks and cleanup, and a systemd service unit with `Restart=on-failure` and `PYTHONUNBUFFERED=1`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Capture cadence & recovery
- Default capture interval: 1 minute (configurable in YAML)
- Failed capture logging: log to file if configured, otherwise skip silently (opt-in gap tracking)

#### Storage thresholds & cleanup
- Hard stop threshold: 90% disk usage -- daemon refuses to write new captures
- Default retention period: 30 days (configurable in YAML)
- Auto-cleanup: off by default -- user must explicitly enable in config
- Cleanup unit: oldest full days first -- removes entire day directories to keep complete days intact

#### Image quality & naming
- Default JPEG quality: 85% (configurable in YAML)
- Resolution: capture at native resolution up to 1080p, downscale if camera provides higher; configurable override in YAML
- Naming collisions: skip duplicate if a file already exists for that second
- Default storage path: ~/timelapse-images (configurable); setup script/docs should mention /var/lib/timelapse as an alternative for production installs

#### Service & logging behavior
- Log verbosity: errors + camera connect/disconnect events (not every capture)
- Installation: setup script for quick install + thorough documentation so existing installations remain transparent and configurable

### Claude's Discretion
- Camera disconnect recovery strategy (retry timing, backoff)
- Config hot-reload vs restart-required
- Log destination (systemd journal, file, or both)
- Status reporting mechanism (JSON file vs systemd status vs other)
- Exact progress/status format

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAP-01 | Camera auto-detects Pi Camera (picamera2/libcamera) or USB webcam (OpenCV/v4l2) at startup | Camera abstraction layer with detection logic; picamera2 for Pi Camera, OpenCV for USB only (confirmed incompatibility on Bookworm); use `v4l2-ctl --list-devices` and picamera2 instantiation for detection |
| CAP-02 | Camera source is configurable (auto, picamera, usb) via YAML config | YAML config with `camera.source: auto|picamera|usb`; PyYAML safe_load pattern; validated at startup |
| CAP-03 | Images captured at configurable interval (default 30 seconds) | Note: user decision overrides to 1-minute default. Sleep loop with drift correction; keep camera pipeline open between captures |
| CAP-04 | Images saved with ISO 8601 timestamps in date-organized directories (YYYY/MM/DD/HHMMSS.jpg) | `pathlib` for directory creation; `datetime.strftime` for naming; NTP sync check via `time-sync.target` systemd dependency |
| CAP-05 | Capture daemon runs as a systemd service with auto-start and restart-on-crash | systemd unit file with `Type=simple`, `Restart=on-failure`, `PYTHONUNBUFFERED=1`; service depends on `time-sync.target` |
| CAP-06 | All settings stored in a single YAML configuration file | PyYAML 6.x with `safe_load`; config validation at startup; SIGHUP reload recommended |
| CAP-07 | JPEG quality is configurable (trade storage for image quality) | picamera2: use `capture_image()` + PIL `Image.save(quality=N)` (no native quality param in `capture_file`); OpenCV: `cv2.imwrite` with `IMWRITE_JPEG_QUALITY` flag |
| CAP-08 | Storage output directory is configurable (SD card, USB drive, NAS mount) | Config `storage.output_dir` with `pathlib.Path`; validate directory exists and is writable at startup |
| CAP-09 | Capture subprocess uses timeouts to prevent hangs (max 30s per capture) | picamera2: set frame timeout; OpenCV: `cap.read()` with timeout wrapper; Python `signal.alarm` or threading timer as fallback |
| CAP-10 | Camera lock file prevents simultaneous access between daemon and web server | `fcntl.flock` with `LOCK_EX | LOCK_NB` on `/tmp/timelapse-camera.lock`; non-blocking so web server live view can fail gracefully |
| STR-01 | Optional auto-cleanup deletes images older than N days (configurable, off by default) | Storage manager scans date directories, compares to retention threshold, removes oldest full days; off by default per user decision |
| STR-02 | Disk space monitored with configurable warning threshold (default 15% free) | `shutil.disk_usage(output_dir)` calculates `free/total * 100`; log warning when below threshold |
| STR-03 | Pre-capture disk space check prevents writing when disk is critically full | Check `shutil.disk_usage()` before every capture; refuse to write at 90% usage (user decision); log error |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **picamera2** | 0.3.33+ | Pi Camera Module capture via libcamera | Official Raspberry Pi Foundation library. Only supported way to use Pi Camera on Bookworm+. Pre-installed via `apt`. OpenCV VideoCapture does NOT work with Pi Camera on libcamera stack. |
| **opencv-python-headless** | 4.9+ | USB webcam capture via V4L2 | `cv2.VideoCapture` with `CAP_V4L2` is the standard for USB webcams on Linux. Headless variant skips GUI deps. Installed via `apt` as `python3-opencv`. |
| **PyYAML** | 6.0.x | YAML configuration file parsing | Widely used, stable. `safe_load()` prevents code execution. Latest: 6.0.3. |
| **Python** | 3.11.2+ | Runtime | Default on Raspberry Pi OS Bookworm. PEP 668 requires venv with `--system-site-packages` for camera library access. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pathlib** | stdlib | File path management | All path operations -- directory creation, file existence checks, glob patterns |
| **shutil** | stdlib | Disk space monitoring | `shutil.disk_usage()` for pre-capture checks and threshold warnings |
| **fcntl** | stdlib | File-based camera lock | Inter-process camera mutex via `flock(LOCK_EX)` between daemon and web server |
| **signal** | stdlib | SIGHUP config reload | Register handler for `SIGHUP` to reload YAML config without restart |
| **logging** | stdlib | Structured logging | Python's built-in logging module routed to systemd journal via stdout/stderr |
| **PIL/Pillow** | system | JPEG quality control for picamera2 | `Image.save(quality=N)` since picamera2's `capture_file()` lacks quality parameter |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `fcntl.flock` | `filelock` (PyPI) | Cross-platform, cleaner API, but adds a dependency for Unix-only project; `fcntl.flock` is sufficient |
| `PyYAML` | `tomllib` (stdlib 3.11+) | No external dependency, but YAML has broader Pi community familiarity and supports comments natively; TOML read-only in stdlib (no write) |
| `time.sleep()` loop | `threading.Timer` | Drift correction, but added complexity; simple sleep with elapsed-time adjustment is sufficient |
| picamera2 `capture_file()` | picamera2 `capture_image()` + PIL save | Required for JPEG quality control; `capture_file()` has no quality parameter |
| Manual retry logic | `tenacity` or `backoff` (PyPI) | Cleaner decorator API, but adds dependency for a single use; manual backoff is ~10 lines |

**Installation:**

```bash
# System packages (Raspberry Pi OS Bookworm)
sudo apt install -y python3-picamera2 python3-opencv ffmpeg

# Create venv with system-site-packages access (required for picamera2 and cv2)
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Python packages via pip
pip install pyyaml

# Development dependencies
pip install pytest pytest-cov
```

## Architecture Patterns

### Recommended Project Structure

```
rpi-timelapse-cam/
├── src/
│   └── timelapse/
│       ├── __init__.py
│       ├── __main__.py          # Entry point: `python -m timelapse`
│       ├── daemon.py            # Main capture loop, signal handling
│       ├── config.py            # YAML config loading, validation, defaults
│       ├── camera/
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract CameraBackend interface
│       │   ├── picamera.py      # Pi Camera backend (picamera2)
│       │   ├── usb.py           # USB webcam backend (OpenCV)
│       │   └── detect.py        # Auto-detection logic
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── manager.py       # Disk checks, cleanup, directory creation
│       │   └── cleanup.py       # Age-based cleanup of day directories
│       └── lock.py              # Camera lock file (fcntl.flock)
├── config/
│   └── timelapse.yml            # Default/example config
├── systemd/
│   └── timelapse-capture.service  # systemd unit file
├── scripts/
│   └── setup.sh                 # Quick install script
├── tests/
│   ├── test_config.py
│   ├── test_camera_detect.py
│   ├── test_storage.py
│   └── test_daemon.py
├── pyproject.toml               # Project metadata and dependencies
└── README.md
```

### Pattern 1: Camera Abstraction Layer

**What:** Abstract base class with two concrete implementations. Auto-detection at startup tries picamera2 first, falls back to OpenCV.

**When to use:** Always -- the daemon must support both camera types through a unified interface.

**Example:**

```python
# src/timelapse/camera/base.py
from abc import ABC, abstractmethod
from pathlib import Path

class CameraBackend(ABC):
    """Abstract interface for camera capture backends."""

    @abstractmethod
    def open(self) -> None:
        """Initialize and open the camera. Keep pipeline open for reuse."""
        ...

    @abstractmethod
    def capture(self, output_path: Path, quality: int = 85) -> bool:
        """Capture a single image. Returns True on success."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Release camera resources."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this camera type is currently available."""
        ...
```

```python
# src/timelapse/camera/picamera.py
from pathlib import Path
from timelapse.camera.base import CameraBackend

class PiCameraBackend(CameraBackend):
    def __init__(self, resolution=(1920, 1080)):
        self._camera = None
        self._resolution = resolution

    def open(self):
        from picamera2 import Picamera2
        self._camera = Picamera2()
        config = self._camera.create_still_configuration(
            main={"size": self._resolution}
        )
        self._camera.configure(config)
        self._camera.start()
        # Allow AE/AWB to settle
        import time
        time.sleep(2)

    def capture(self, output_path: Path, quality: int = 85) -> bool:
        """Capture via PIL for JPEG quality control."""
        img = self._camera.capture_image("main")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), quality=quality)
        return True

    def close(self):
        if self._camera:
            self._camera.stop()
            self._camera.close()

    def is_available(self) -> bool:
        try:
            from picamera2 import Picamera2
            cam = Picamera2()
            cam.close()
            return True
        except Exception:
            return False
```

```python
# src/timelapse/camera/usb.py
import cv2
from pathlib import Path
from timelapse.camera.base import CameraBackend

class USBCameraBackend(CameraBackend):
    def __init__(self, device_index=0, resolution=(1920, 1080)):
        self._cap = None
        self._device_index = device_index
        self._resolution = resolution

    def open(self):
        self._cap = cv2.VideoCapture(self._device_index, cv2.CAP_V4L2)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open USB camera at index {self._device_index}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[0])
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[1])
        # Allow auto-exposure to settle
        import time
        time.sleep(0.5)

    def capture(self, output_path: Path, quality: int = 85) -> bool:
        ret, frame = self._cap.read()
        if not ret:
            return False
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(
            str(output_path), frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        )
        return True

    def close(self):
        if self._cap:
            self._cap.release()

    def is_available(self) -> bool:
        try:
            cap = cv2.VideoCapture(self._device_index, cv2.CAP_V4L2)
            available = cap.isOpened()
            cap.release()
            return available
        except Exception:
            return False
```

**Source:** [picamera2 official timelapse example](https://github.com/raspberrypi/picamera2/blob/main/examples/capture_timelapse.py), [OpenCV VideoCapture docs](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html)

### Pattern 2: Keep Camera Open Between Captures

**What:** Start the camera once, capture in a loop, stop only on shutdown. Avoids 1-2 second overhead of restarting the camera pipeline per capture.

**When to use:** Always. Stopping and restarting the camera between captures adds significant latency (especially picamera2) and causes auto-exposure flicker.

**Key detail from picamera2 forums:** With the camera free-running, the gap between captures is on the order of milliseconds. With stop/start per capture, it is 1+ seconds.

**Example:**

```python
# src/timelapse/daemon.py - core loop (simplified)
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class CaptureDaemon:
    def __init__(self, config, camera, storage):
        self._config = config
        self._camera = camera
        self._storage = storage
        self._running = False

    def run(self):
        self._running = True
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGHUP, self._handle_reload)

        self._camera.open()
        logger.info("Camera opened, starting capture loop")

        try:
            while self._running:
                loop_start = time.monotonic()
                self._capture_once()
                # Drift-corrected sleep
                elapsed = time.monotonic() - loop_start
                sleep_time = max(0, self._config.interval - elapsed)
                time.sleep(sleep_time)
        finally:
            self._camera.close()
            logger.info("Camera closed, daemon stopped")

    def _capture_once(self):
        # Pre-capture disk check
        if not self._storage.has_space():
            logger.error("Disk usage exceeds threshold, skipping capture")
            return

        now = datetime.now()
        output_path = self._storage.image_path(now)

        # Skip if file already exists (collision avoidance)
        if output_path.exists():
            return

        try:
            success = self._camera.capture(output_path, self._config.jpeg_quality)
            if not success:
                logger.error("Capture returned failure")
        except Exception:
            logger.exception("Capture failed")

        # Run cleanup if enabled
        if self._config.cleanup_enabled:
            self._storage.cleanup_old_days(self._config.retention_days)
```

**Source:** [picamera2 timelapse discussions](https://forums.raspberrypi.com/viewtopic.php?t=348494), [picamera2 efficient capture thread](https://forums.raspberrypi.com/viewtopic.php?t=363106)

### Pattern 3: Camera Lock File

**What:** File-based mutex using `fcntl.flock()` to prevent simultaneous camera access between the capture daemon and the future web server live view.

**When to use:** Every capture. The daemon holds an exclusive lock during capture, releases immediately after. The web server (Phase 2) will attempt a non-blocking lock for live view and gracefully fail if the daemon is mid-capture.

**Example:**

```python
# src/timelapse/lock.py
import fcntl
from pathlib import Path
from contextlib import contextmanager

LOCK_PATH = Path("/tmp/timelapse-camera.lock")

@contextmanager
def camera_lock(blocking=True):
    """Acquire exclusive camera lock. Non-blocking raises BlockingIOError."""
    lock_file = open(LOCK_PATH, "w")
    try:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        fcntl.flock(lock_file, flags)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        yield lock_file
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
```

**Source:** [Python fcntl documentation](https://docs.python.org/3/library/fcntl.html), [fcntl.flock patterns](https://gist.github.com/jirihnidek/430d45c54311661b47fb45a3a7846537)

### Pattern 4: Pre-Capture Disk Space Check

**What:** Check `shutil.disk_usage()` before every capture. Refuse to write when disk usage exceeds the configured threshold (90% per user decision).

**Example:**

```python
# src/timelapse/storage/manager.py
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self, output_dir: Path, stop_threshold: float = 90.0,
                 warn_threshold: float = 85.0):
        self._output_dir = output_dir
        self._stop_threshold = stop_threshold
        self._warn_threshold = warn_threshold

    def disk_usage_percent(self) -> float:
        """Return disk usage as percentage (0-100)."""
        usage = shutil.disk_usage(self._output_dir)
        return (usage.used / usage.total) * 100

    def has_space(self) -> bool:
        """Return True if disk usage is below the hard stop threshold."""
        percent = self.disk_usage_percent()
        if percent >= self._stop_threshold:
            return False
        if percent >= self._warn_threshold:
            logger.warning("Disk usage at %.1f%%, approaching limit", percent)
        return True

    def image_path(self, timestamp: datetime) -> Path:
        """Generate the full path for an image: output_dir/YYYY/MM/DD/HHMMSS.jpg"""
        return (self._output_dir
                / timestamp.strftime("%Y")
                / timestamp.strftime("%m")
                / timestamp.strftime("%d")
                / f"{timestamp.strftime('%H%M%S')}.jpg")

    def cleanup_old_days(self, retention_days: int) -> int:
        """Delete day directories older than retention_days. Returns count deleted."""
        cutoff = datetime.now() - timedelta(days=retention_days)
        deleted = 0
        # Walk year/month/day structure
        for year_dir in sorted(self._output_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                for day_dir in sorted(month_dir.iterdir()):
                    if not day_dir.is_dir():
                        continue
                    try:
                        dir_date = datetime.strptime(
                            f"{year_dir.name}/{month_dir.name}/{day_dir.name}",
                            "%Y/%m/%d"
                        )
                        if dir_date < cutoff:
                            shutil.rmtree(day_dir)
                            deleted += 1
                            logger.info("Cleaned up day directory: %s", day_dir)
                    except ValueError:
                        continue  # Skip non-date directories
        return deleted
```

**Source:** [Python shutil.disk_usage() docs](https://docs.python.org/3/library/shutil.html), [GeeksforGeeks shutil.disk_usage](https://www.geeksforgeeks.org/python/python-shutil-disk_usage-method/)

### Pattern 5: systemd Service Unit

**What:** The daemon runs as a systemd service with auto-restart, journal logging, and time-sync dependency.

**Example:**

```ini
# systemd/timelapse-capture.service
[Unit]
Description=Timelapse Capture Daemon
After=time-sync.target
Wants=time-sync.target

[Service]
Type=simple
User=pi
Group=video
ExecStart=/home/pi/rpi-timelapse-cam/venv/bin/python -m timelapse --config /home/pi/timelapse-config.yml
Restart=on-failure
RestartSec=5
StartLimitBurst=5
StartLimitIntervalSec=300
Environment=PYTHONUNBUFFERED=1
StandardOutput=journal
StandardError=journal
SyslogIdentifier=timelapse-capture

# Resource limits
MemoryMax=256M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

**Key details:**
- `After=time-sync.target` ensures NTP clock is synced before captures start (Pi has no RTC)
- `User=pi, Group=video` runs as non-root with camera hardware access
- `PYTHONUNBUFFERED=1` ensures Python output reaches journal immediately
- `Restart=on-failure` with `RestartSec=5` and burst limits prevents crash loops
- `MemoryMax=256M` prevents the daemon from consuming all RAM on constrained Pi models

**Source:** [Raspberry Pi Forums systemd restart](https://forums.raspberrypi.com/viewtopic.php?t=324417), [Python systemd watchdog example](https://gist.github.com/Spindel/1d07533ef94a4589d348)

### Anti-Patterns to Avoid

- **Stopping and restarting camera per capture:** Adds 1-2 seconds latency, causes auto-exposure flicker. Keep camera pipeline open.
- **Using `cv2.VideoCapture(0)` for Pi Camera on Bookworm:** Does NOT work. OpenCV's V4L2 backend is incompatible with libcamera. Use picamera2 for Pi Camera, OpenCV only for USB webcams.
- **Using `yaml.load()` (unsafe):** Always use `yaml.safe_load()`. The unsafe loader can execute arbitrary Python code.
- **Using `os.path` instead of `pathlib`:** pathlib is the modern Python standard. More readable, safer, better method chaining.
- **Using cron for sub-minute intervals:** Cron's minimum resolution is 1 minute. A long-running daemon with sleep loop is the correct pattern.
- **Capturing to a flat directory:** Performance collapses after 50,000+ files. Date-organized hierarchy is essential from day one.
- **Running as root:** The daemon needs video group membership, not root. Use systemd `User=` directive.
- **Ignoring NTP sync at boot:** Pi has no RTC. Timestamps will be wrong (epoch or last-shutdown time) until NTP syncs. Depend on `time-sync.target`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JPEG quality control (picamera2) | Custom encoder | PIL `Image.save(quality=N)` via `capture_image()` | picamera2's `capture_file()` has no quality parameter; PIL is the official workaround |
| Disk space monitoring | Custom statvfs calls | `shutil.disk_usage()` | Stdlib, cross-platform, returns named tuple with total/used/free |
| Camera lock file | Custom PID file with polling | `fcntl.flock()` context manager | OS-managed lock, auto-releases on process death, no stale locks |
| YAML config parsing | Custom parser or `json` | `PyYAML.safe_load()` | Human-readable, supports comments, widely used in Pi community |
| Process management | Custom daemonization | systemd service unit | Handles forking, logging, restart, boot-start. Already running on every Pi |
| Camera device detection | Manual `/dev/video*` scanning | picamera2 instantiation test + `cv2.VideoCapture.isOpened()` | Each library knows best how to detect its own hardware |
| Exponential backoff | Complex retry framework | Simple manual backoff (~10 lines) | Only one retry point (camera reconnect); a library is overkill |

**Key insight:** The Pi ecosystem provides standard solutions for every infrastructure concern in this phase. Custom code should focus on the capture loop logic and storage policy -- everything else has a stdlib or system-level solution.

## Common Pitfalls

### Pitfall 1: picamera2 JPEG Quality Trap

**What goes wrong:** Developer uses `picam2.capture_file("photo.jpg")` and gets low-quality JPEGs (~2MB for a 4056x3040 image, vs 6-10MB expected). Quality cannot be configured.

**Why it happens:** picamera2's `capture_file()` uses a fixed internal JPEG quality setting. There is no `quality` parameter on the method.

**How to avoid:** Use `capture_image("main")` to get a PIL Image object, then call `img.save(path, quality=85)`. This gives full control over JPEG compression.

**Warning signs:** File sizes much smaller than expected for the resolution.

**Source:** [picamera2 issue #431](https://github.com/raspberrypi/picamera2/issues/431)

### Pitfall 2: OpenCV VideoCapture with Pi Camera on Bookworm

**What goes wrong:** `cv2.VideoCapture(0)` silently fails or returns empty frames when used with a Pi Camera Module on Raspberry Pi OS Bookworm.

**Why it happens:** The libcamera stack used by modern Pi Camera Modules is NOT compatible with OpenCV's V4L2 backend. This is a known upstream issue (opencv/opencv#21653).

**How to avoid:** Never use OpenCV for Pi Camera capture. Use picamera2 exclusively for Pi Camera. Use OpenCV only for USB webcams. The camera abstraction layer must be two genuinely separate backends, not two paths through OpenCV.

**Warning signs:** `VIDEOIO(V4L2:/dev/video0): select() timeout` errors, empty frames, black images.

**Source:** [OpenCV issue #21653](https://github.com/opencv/opencv/issues/21653), [Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=372690)

### Pitfall 3: NTP Clock Sync on Boot

**What goes wrong:** First captures after boot have wrong timestamps (year 1970, or last-shutdown time). Image files are written to incorrect date directories, corrupting the timeline.

**Why it happens:** Raspberry Pi has no battery-backed real-time clock. At boot, the clock is set to epoch (1970) or the last-saved time via fake-hwclock. NTP sync takes seconds to minutes after boot depending on network availability.

**How to avoid:** Make the systemd service depend on `time-sync.target` with `After=time-sync.target` and `Wants=time-sync.target`. Enable `systemd-time-wait-sync.service` if not already enabled. Optionally, add a startup check in the daemon that verifies `timedatectl` shows `System clock synchronized: yes` before starting captures.

**Warning signs:** Images dated 1970 or with yesterday's date appearing after reboot.

**Source:** [Raspberry Pi Forums NTP check](https://forums.raspberrypi.com/viewtopic.php?t=320988)

### Pitfall 4: Disk Full Crashes Entire System

**What goes wrong:** At 1-minute intervals with ~750KB average JPEG size, ~1 GB/day accumulates. A 32GB SD card fills in ~3-4 weeks. When storage hits 100%, OS logging fails, services crash, Pi becomes unresponsive and may require physical intervention.

**Why it happens:** Storage management is deferred as a "nice-to-have." The capture loop writes without checking available space.

**How to avoid:** Check `shutil.disk_usage()` before every capture. Refuse to write at 90% disk usage (user decision). When auto-cleanup is enabled, delete oldest full day directories. Log clearly when captures are skipped due to disk pressure.

**Warning signs:** Decreasing free space trend without cleanup. Captures suddenly stopping with no error.

**Source:** [Python shutil docs](https://docs.python.org/3/library/shutil.html)

### Pitfall 5: Camera Hang Freezes Daemon

**What goes wrong:** USB webcam disconnects or GPU memory fault causes the capture call to hang indefinitely. The daemon stops capturing, the sleep loop never advances, and captures are silently missed.

**Why it happens:** Neither `picam2.capture_image()` nor `cap.read()` have built-in timeouts in all failure modes. Hardware faults can cause blocking reads.

**How to avoid:** Wrap capture calls in a timeout mechanism. Options: (a) `threading.Timer` that calls `thread.interrupt_main()`, (b) `signal.alarm(30)` for Unix alarm, (c) run capture in a separate thread with `thread.join(timeout=30)`. If capture times out, log the error, attempt camera reconnection with exponential backoff.

**Warning signs:** Daemon process exists but last capture timestamp is stale. systemd shows service as "running" but no new images appearing.

### Pitfall 6: PEP 668 Virtual Environment Requirement

**What goes wrong:** `pip install pyyaml` fails with "externally-managed-environment" error on Bookworm.

**Why it happens:** Raspberry Pi OS Bookworm enforces PEP 668. System Python is protected from pip installs.

**How to avoid:** Always create a venv with `python3 -m venv --system-site-packages venv`. The `--system-site-packages` flag is required to access `picamera2` and `cv2` which are installed as system packages via `apt`.

**Warning signs:** `error: externally-managed-environment` from pip.

**Source:** [Raspberry Pi documentation](https://www.raspberrypi.com/documentation/computers/os.html)

## Code Examples

Verified patterns from official sources:

### picamera2 Timelapse Capture (Keep Camera Open)

```python
# Source: https://github.com/raspberrypi/picamera2/blob/main/examples/capture_timelapse.py
from picamera2 import Picamera2
import time

picam2 = Picamera2()
picam2.configure("still")
picam2.start()

# Allow AE/AWB to settle before optionally disabling them
time.sleep(1)
picam2.set_controls({"AeEnable": False, "AwbEnable": False, "FrameRate": 1.0})
time.sleep(1)

for i in range(1, 51):
    r = picam2.capture_request()
    r.save("main", f"image{i}.jpg")
    r.release()

picam2.stop()
```

### picamera2 Capture with JPEG Quality Control

```python
# Source: https://github.com/raspberrypi/picamera2/issues/431
from picamera2 import Picamera2
from pathlib import Path

picam2 = Picamera2()
config = picam2.create_still_configuration(main={"size": (1920, 1080)})
picam2.configure(config)
picam2.start()

# capture_image returns a PIL Image object
img = picam2.capture_image("main")
img.save("/path/to/output.jpg", quality=85)

picam2.stop()
```

### OpenCV USB Webcam Capture with Quality

```python
# Source: https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html
import cv2
from pathlib import Path

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
if not cap.isOpened():
    raise RuntimeError("Cannot open USB camera")

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

ret, frame = cap.read()
if ret:
    cv2.imwrite(
        "/path/to/output.jpg", frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), 85]
    )

cap.release()
```

### PyYAML Safe Configuration Loading

```python
# Source: https://pyyaml.org/wiki/PyYAMLDocumentation
import yaml
from pathlib import Path

def load_config(config_path: Path) -> dict:
    """Load and validate YAML configuration."""
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise SystemExit(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise SystemExit(f"Invalid YAML in config: {e}")

    # Apply defaults
    defaults = {
        "capture": {
            "interval": 60,
            "source": "auto",
            "jpeg_quality": 85,
            "resolution": [1920, 1080],
        },
        "storage": {
            "output_dir": str(Path.home() / "timelapse-images"),
            "stop_threshold": 90,
            "warn_threshold": 85,
            "cleanup_enabled": False,
            "retention_days": 30,
        },
    }
    # Deep merge config over defaults
    return _deep_merge(defaults, config or {})
```

### SIGHUP Config Reload

```python
# Source: https://medium.com/@snnapys-devops/keep-your-python-running-reloading-configuration-on-the-fly-with-sighup-8cac1179c24d
import signal
import logging

logger = logging.getLogger(__name__)

class CaptureDaemon:
    def __init__(self, config_path):
        self._config_path = config_path
        self._config = load_config(config_path)

    def _handle_reload(self, signum, frame):
        """Reload config on SIGHUP without restarting."""
        logger.info("SIGHUP received, reloading configuration")
        try:
            new_config = load_config(self._config_path)
            self._config = new_config
            logger.info("Configuration reloaded successfully")
        except Exception:
            logger.exception("Failed to reload config, keeping current")
```

### Camera Lock File

```python
# Source: https://docs.python.org/3/library/fcntl.html
import fcntl
import os
from contextlib import contextmanager

@contextmanager
def camera_lock(lock_path="/tmp/timelapse-camera.lock", blocking=True):
    """Context manager for camera access mutex."""
    fd = open(lock_path, "w")
    try:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        fcntl.flock(fd, flags)
        fd.write(f"{os.getpid()}\n")
        fd.flush()
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
```

## Discretion Recommendations

Research findings on areas left to Claude's discretion:

### Camera Disconnect Recovery: Exponential Backoff

**Recommendation:** Manual exponential backoff with jitter and a maximum cap.

**Strategy:**
1. On capture failure, increment a consecutive-failure counter
2. Backoff delay: `min(base * 2^failures + random(0, 1), max_delay)`
3. Base: 5 seconds. Max delay: 300 seconds (5 minutes).
4. On successful capture, reset counter to 0
5. Log camera disconnect at WARNING level (per user decision on logging verbosity)
6. Log reconnection at INFO level

**Rationale:** A dependency like `tenacity` is overkill for a single retry point. Manual backoff is ~10 lines and gives full control. The 5-minute cap prevents the daemon from sleeping too long if the camera is physically reattached. Jitter prevents thundering-herd effects if multiple processes are involved (relevant when web server is added in Phase 2).

### Config Hot-Reload: SIGHUP Signal

**Recommendation:** Support `SIGHUP` for config reload. Do NOT require daemon restart for config changes.

**Rationale:** SIGHUP is the Unix convention for daemon config reload. It is explicit (user sends signal when ready), avoids the risk of loading partially-written files that inotify/watchdog would cause, and requires zero external dependencies. Implementation is ~15 lines: register a signal handler that re-reads the YAML file with error handling to keep the current config on parse failure.

**What reloads:** Capture interval, JPEG quality, storage thresholds, cleanup settings, log verbosity.
**What does NOT reload (requires restart):** Camera source, resolution, storage output directory (structural changes).

### Log Destination: systemd Journal via stdout

**Recommendation:** Log to stdout/stderr using Python's `logging` module. systemd captures this into the journal automatically.

**Rationale:** The systemd service unit sets `StandardOutput=journal` and `StandardError=journal`. Python's logging module writes to stderr by default. With `PYTHONUNBUFFERED=1`, output reaches the journal immediately. This approach:
- Requires zero configuration (no log file paths, rotation, etc.)
- Works with `journalctl -u timelapse-capture` for viewing
- Supports `journalctl --since "1 hour ago"` for filtering
- Persists across reboots if journal persistence is enabled
- No risk of filling disk with log files

No separate log file is needed. Users who want file logging can configure journald to persist or use `journalctl > /path/to/file`.

### Status Reporting: JSON Status File

**Recommendation:** Write a JSON status file at a configurable path (default: `/tmp/timelapse-status.json`) after each capture cycle.

**Rationale:** Phase 2's web UI needs to display daemon status (last capture time, camera type, disk usage, error count). A JSON file is the simplest cross-process communication mechanism -- the web server just reads the file. No IPC, no sockets, no shared memory. The file is atomic-write safe (write to temp, rename) and survives daemon restarts.

**Format:**

```json
{
    "daemon": "running",
    "camera": "picamera",
    "last_capture": "2026-02-16T14:30:00",
    "last_capture_success": true,
    "consecutive_failures": 0,
    "captures_today": 847,
    "disk_usage_percent": 42.3,
    "disk_free_gb": 18.7,
    "uptime_seconds": 86400,
    "config_loaded": "2026-02-16T08:00:00"
}
```

The status file is written atomically (write temp file, then `os.rename`) to prevent the web server from reading a partially-written file.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `picamera` (v1) Python library | `picamera2` (v2) with libcamera | 2022-2023 (Bullseye/Bookworm) | Cannot use old library on modern Pi OS. picamera2 has different API. |
| `raspistill` / `raspivid` CLI | `rpicam-still` / `rpicam-vid` CLI | 2023 (Bookworm) | Old commands removed. Renamed from `libcamera-still` to `rpicam-still`. |
| `cv2.VideoCapture(0)` for Pi Camera | picamera2 only for Pi Camera | 2022+ (libcamera stack) | OpenCV cannot access Pi Camera via V4L2 on libcamera. USB webcams still work. |
| `pip install` globally on Pi | venv with `--system-site-packages` | 2023 (Bookworm, PEP 668) | System Python is externally managed. Must use venv for pip installs. |
| Python 3.9 on Pi OS | Python 3.11.2 on Bookworm | 2023 | f-strings, match statements, tomllib available. Faster runtime. |

**Deprecated/outdated:**
- `picamera` (v1): Does not work with libcamera. Use `picamera2`.
- `raspistill` / `raspivid`: Removed from Bookworm. Use `rpicam-still` / `rpicam-vid`.
- `fswebcam`: Last release ~2014. Unmaintained. Use OpenCV for USB webcams.
- Global `pip install` on Pi OS Bookworm: Blocked by PEP 668. Use venv.

## Open Questions

1. **picamera2 capture timeout behavior**
   - What we know: `capture_image()` and `capture_request()` can hang in some hardware failure scenarios. The picamera2 API does not expose an explicit timeout parameter on these calls.
   - What's unclear: Whether picamera2 has any internal timeout mechanism or whether the daemon must implement its own via threading/signal.
   - Recommendation: Implement a threading-based timeout wrapper (run capture in a thread, join with timeout). Test on actual hardware to determine if picamera2 has implicit timeouts. LOW confidence this is needed in practice but HIGH impact if it is.

2. **Raspberry Pi OS Trixie (next release)**
   - What we know: The latest Raspberry Pi OS is based on Debian Trixie. Python version may differ from 3.11.
   - What's unclear: Whether Trixie is widely adopted yet, and whether picamera2/opencv packages are available.
   - Recommendation: Target Bookworm as minimum. Python 3.11+ ensures compatibility. Test on Trixie when available but do not block on it.

3. **USB webcam device index stability**
   - What we know: USB device indices can change between reboots or when devices are plugged/unplugged. `cv2.VideoCapture(0)` may not always point to the same camera.
   - What's unclear: Whether the `cv2-enumerate-cameras` package (v1.3.3) works reliably on Raspberry Pi OS for device discovery by name/VID/PID.
   - Recommendation: Support configurable device index in YAML. For auto-detection, try index 0 first. Document that users may need to specify the index if they have multiple USB devices. Defer VID/PID-based detection to a future enhancement.

4. **picamera2 focus drift in long-running timelapse**
   - What we know: One user reported focus drift over time with Camera Module 3 (autofocus model). Images become increasingly blurry.
   - What's unclear: Whether this affects Camera Module 2 (fixed focus) or only Module 3. Whether periodic autofocus recalibration helps.
   - Recommendation: Document this as a known issue. For Camera Module 3, consider periodic `AfTrigger` control. For Camera Module 2, this is not applicable. LOW priority -- most plant timelapse users will use fixed-focus cameras.

## Sources

### Primary (HIGH confidence)
- [picamera2 official timelapse example](https://github.com/raspberrypi/picamera2/blob/main/examples/capture_timelapse.py) -- capture loop pattern, AE/AWB control
- [picamera2 PyPI](https://pypi.org/project/picamera2/) -- version 0.3.33, release date Feb 2026
- [picamera2 JPEG quality issue #431](https://github.com/raspberrypi/picamera2/issues/431) -- confirmed no quality param in capture_file; PIL workaround
- [picamera2 Image Capture (DeepWiki)](https://deepwiki.com/raspberrypi/picamera2/3.1-image-capture) -- capture methods, configuration API
- [OpenCV VideoCapture tutorial](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html) -- frame capture, JPEG quality flags
- [Python fcntl documentation](https://docs.python.org/3/library/fcntl.html) -- flock for camera lock
- [Python shutil documentation](https://docs.python.org/3/library/shutil.html) -- disk_usage() API
- [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation) -- safe_load patterns
- [Raspberry Pi OS documentation](https://www.raspberrypi.com/documentation/computers/os.html) -- PEP 668, system packages

### Secondary (MEDIUM confidence)
- [Raspberry Pi Forums: picamera2 timelapse](https://forums.raspberrypi.com/viewtopic.php?t=348494) -- keep-camera-open pattern, performance comparison
- [Raspberry Pi Forums: efficient capture](https://forums.raspberrypi.com/viewtopic.php?t=363106) -- free-running vs stop/start latency
- [Raspberry Pi Forums: NTP sync check](https://forums.raspberrypi.com/viewtopic.php?t=320988) -- timedatectl check, time-sync.target
- [Raspberry Pi Forums: OpenCV Pi Camera Bookworm](https://forums.raspberrypi.com/viewtopic.php?t=372690) -- confirmed incompatibility
- [OpenCV issue #21653](https://github.com/opencv/opencv/issues/21653) -- VideoCapture + libcamera incompatibility
- [cv2-enumerate-cameras PyPI](https://pypi.org/project/cv2-enumerate-cameras/) -- v1.3.3, device discovery
- [SIGHUP config reload pattern](https://medium.com/@snnapys-devops/keep-your-python-running-reloading-configuration-on-the-fly-with-sighup-8cac1179c24d) -- signal-based reload
- [systemd watchdog with Python](https://gist.github.com/Spindel/1d07533ef94a4589d348) -- notify/watchdog patterns
- [Raspberry Pi Forums: systemd restart](https://forums.raspberrypi.com/viewtopic.php?t=324417) -- service unit best practices
- [filelock PyPI](https://pypi.org/project/filelock/) -- alternative to fcntl considered

### Tertiary (LOW confidence)
- picamera2 focus drift report -- single user, Camera Module 3 specific, may not be reproducible
- Raspberry Pi OS Trixie availability -- mentioned in search results but adoption unclear
- cv2-enumerate-cameras on Raspberry Pi -- untested on ARM/Pi OS specifically

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- picamera2, OpenCV, PyYAML are well-established with verified versions and APIs. Key compatibility issue (OpenCV + Pi Camera on Bookworm) confirmed via multiple sources.
- Architecture: HIGH -- patterns verified against official picamera2 examples, community forum solutions, and Python stdlib documentation. Keep-camera-open pattern confirmed by picamera2 maintainers.
- Pitfalls: HIGH -- critical issues (JPEG quality trap, VideoCapture incompatibility, NTP sync, disk full) confirmed by official issue trackers and multiple community reports.
- Discretion areas: MEDIUM -- recommendations based on well-established Unix patterns (SIGHUP, journal logging, JSON status files) but not specifically validated for this project.

**Research date:** 2026-02-16
**Valid until:** 2026-03-16 (30 days -- stable ecosystem, picamera2 actively maintained but API stable)
