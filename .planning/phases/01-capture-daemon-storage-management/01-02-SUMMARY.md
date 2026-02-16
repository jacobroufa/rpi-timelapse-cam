---
phase: 01-capture-daemon-storage-management
plan: 02
subsystem: camera
tags: [picamera2, opencv, camera-abstraction, fcntl, threading, abc]

# Dependency graph
requires: []
provides:
  - "Abstract CameraBackend interface (ABC with open/capture/close/is_available)"
  - "PiCameraBackend using picamera2 with PIL JPEG quality control"
  - "USBCameraBackend using OpenCV with IMWRITE_JPEG_QUALITY"
  - "detect_camera() factory with auto/picamera/usb source selection"
  - "capture_with_timeout() threading wrapper (30s default)"
  - "camera_lock() fcntl.flock inter-process mutex"
affects: [01-03-daemon-loop, 02-web-server]

# Tech tracking
tech-stack:
  added: [picamera2, opencv-python-headless, PIL/Pillow]
  patterns: [abstract-backend-interface, lazy-imports, threading-timeout, fcntl-lock]

key-files:
  created:
    - src/timelapse/camera/__init__.py
    - src/timelapse/camera/base.py
    - src/timelapse/camera/picamera.py
    - src/timelapse/camera/usb.py
    - src/timelapse/camera/detect.py
    - src/timelapse/lock.py
  modified: []

key-decisions:
  - "Used capture_image() + PIL save for picamera2 JPEG quality (capture_file has no quality param)"
  - "Lazy imports for picamera2 and cv2 so modules are importable on any machine"
  - "Threaded timeout via daemon thread with join(timeout) for capture hang protection"
  - "camera_lock yields None (not the file object) for cleaner context manager API"

patterns-established:
  - "Lazy hardware imports: all picamera2/cv2 imports at call time, not module level"
  - "Camera backend ABC: subclasses implement open/capture/close/is_available/name"
  - "Auto-detection order: picamera2 first, USB fallback, clear error if neither"
  - "fcntl.flock context manager for inter-process camera mutex"

requirements-completed: [CAP-01, CAP-02, CAP-09, CAP-10]

# Metrics
duration: 3min
completed: 2026-02-16
---

# Phase 1 Plan 2: Camera Abstraction Layer Summary

**Two-backend camera abstraction (picamera2 + OpenCV) with auto-detection, 30s capture timeout, and fcntl lock file for inter-process safety**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-16T22:39:34Z
- **Completed:** 2026-02-16T22:42:52Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Abstract CameraBackend interface with five abstract methods (open, capture, close, is_available, name)
- PiCameraBackend captures via picamera2 with PIL Image.save() for JPEG quality control
- USBCameraBackend captures via OpenCV with IMWRITE_JPEG_QUALITY flag
- Auto-detection tries picamera2 first, falls back to USB, raises clear error listing both failures
- Capture timeout wrapper prevents hangs using daemon thread with configurable timeout (default 30s)
- Camera lock file uses fcntl.flock for inter-process mutex with blocking/non-blocking modes

## Task Commits

Each task was committed atomically:

1. **Task 1: Create camera backends with abstract interface** - `265197e` (feat)
2. **Task 2: Create camera auto-detection, capture timeout, and lock file** - `e9d6da0` (feat)

## Files Created/Modified
- `src/timelapse/camera/base.py` - Abstract CameraBackend ABC defining the backend interface
- `src/timelapse/camera/picamera.py` - Pi Camera backend using picamera2 with lazy imports
- `src/timelapse/camera/usb.py` - USB webcam backend using OpenCV with lazy imports
- `src/timelapse/camera/detect.py` - Auto-detection factory and capture timeout wrapper
- `src/timelapse/camera/__init__.py` - Package re-exports for all camera classes
- `src/timelapse/lock.py` - fcntl.flock camera mutex context manager

## Decisions Made
- Used `capture_image("main")` + PIL `Image.save(quality=N)` for picamera2 instead of `capture_file()` which has no quality parameter (per research finding on JPEG quality trap)
- All hardware library imports are lazy (at call time, not module level) so modules are importable on machines without camera hardware
- Capture timeout uses `threading.Thread` with `daemon=True` and `join(timeout)` rather than `signal.alarm` for thread safety
- `camera_lock()` yields `None` rather than the file object for a cleaner API (callers do not need the lock file)
- `detect_camera()` returns an unopened backend instance -- callers are responsible for calling `open()`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Camera subsystem complete and ready for the daemon loop (Plan 03)
- All modules verified importable on development machine without camera hardware
- Lock file tested with acquire/release cycle
- detect_camera verified to raise clear RuntimeError when no camera is available

## Self-Check: PASSED

All 6 created files verified on disk. Both task commits (265197e, e9d6da0) verified in git log.

---
*Phase: 01-capture-daemon-storage-management*
*Completed: 2026-02-16*
