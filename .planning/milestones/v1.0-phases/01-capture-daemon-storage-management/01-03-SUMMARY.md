---
phase: 01-capture-daemon-storage-management
plan: 03
subsystem: daemon
tags: [systemd, signal-handling, argparse, exponential-backoff, json-status]

# Dependency graph
requires:
  - phase: 01-01
    provides: "Config loader, StorageManager, cleanup_old_days"
  - phase: 01-02
    provides: "CameraBackend, detect_camera, capture_with_timeout, camera_lock"
provides:
  - "CaptureDaemon class with drift-corrected capture loop and error recovery"
  - "CLI entry point (python -m timelapse --config PATH)"
  - "Atomic JSON status file for web UI consumption"
  - "systemd service unit with NTP dependency and crash restart"
  - "Setup script with venv creation and dependency installation"
affects: [02-web-ui, deployment]

# Tech tracking
tech-stack:
  added: []
  patterns: [drift-corrected-sleep, exponential-backoff-recovery, atomic-json-write, signal-handler-reload, systemd-service]

key-files:
  created:
    - src/timelapse/daemon.py
    - src/timelapse/__main__.py
    - src/timelapse/status.py
    - systemd/timelapse-capture.service
    - scripts/setup.sh
  modified: []

key-decisions:
  - "Status file placed in output_dir/.status.json for co-location with images"
  - "Sleep in 0.5s increments for responsive shutdown on SIGTERM"
  - "Backoff formula: min(5 * 2^failures + jitter, 300s) for camera recovery"
  - "SIGHUP reloads interval/quality/thresholds but NOT source/resolution/output_dir"
  - "Config fallback chain: --config flag > /etc/timelapse/timelapse.yml > ./config/timelapse.yml"

patterns-established:
  - "Daemon loop: capture → status write → drift-corrected sleep → repeat"
  - "Error recovery: close camera → backoff sleep → reopen camera"
  - "Status reporting: atomic JSON write via temp file + rename"
  - "Signal handling: SIGTERM/SIGINT=shutdown, SIGHUP=reload"

requirements-completed: [CAP-03, CAP-05]

# Metrics
duration: 5min
completed: 2026-02-16
---

# Phase 1 Plan 3: Capture Daemon, CLI & systemd Summary

**CaptureDaemon with drift-corrected capture loop, exponential backoff recovery, SIGHUP config reload, atomic JSON status, systemd service with NTP dependency**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-16T22:46:00Z
- **Completed:** 2026-02-16T22:51:00Z
- **Tasks:** 2
- **Files created:** 5

## Accomplishments
- CaptureDaemon ties together config, camera, storage into a running daemon with drift-corrected interval sleep
- Pre-capture disk check refuses to write above 90% threshold; cleanup runs after each capture when enabled
- Camera disconnect recovery with exponential backoff (5s base, 300s max, with jitter)
- SIGHUP reloads config without restart; warns about settings that require restart
- Atomic JSON status file enables Phase 2 web UI to read daemon state safely
- systemd unit starts on boot, restarts on crash (max 5 in 5 min), depends on NTP time-sync
- Setup script installs system packages, creates venv with --system-site-packages, copies config

## Task Commits

Each task was committed atomically:

1. **Task 1: Create capture daemon loop, status reporter, and CLI entry point** - `0f8d8b1` (feat)
2. **Task 2: Create systemd service unit and setup script** - `7d14180` (feat)

## Files Created/Modified
- `src/timelapse/daemon.py` - CaptureDaemon class with capture loop, signal handling, backoff recovery
- `src/timelapse/__main__.py` - CLI entry point with --config argument and fallback chain
- `src/timelapse/status.py` - Atomic JSON status file write/read via temp file + rename
- `systemd/timelapse-capture.service` - systemd unit with NTP dependency, crash restart, resource limits
- `scripts/setup.sh` - Install script: system packages, venv, config copy, systemd install

## Decisions Made
- Status file placed at output_dir/.status.json so it's co-located with images
- Sleep in 0.5s increments allows responsive shutdown (< 0.5s after SIGTERM)
- Backoff uses jitter (random 0-1s) to prevent thundering herd on multi-instance setups
- Config reload warns but doesn't apply source/resolution/output_dir changes (require restart)
- Setup script does NOT auto-enable the service — prints instructions for user to decide

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Complete capture daemon ready to run on Raspberry Pi
- Phase 2 (Web UI) can read .status.json for daemon state display
- Phase 3 (Timelapse) can find images in the YYYY/MM/DD directory structure
- No blockers

---
*Phase: 01-capture-daemon-storage-management*
*Completed: 2026-02-16*

## Self-Check: PASSED

All 5 files found. Both task commits (0f8d8b1, 7d14180) verified.
