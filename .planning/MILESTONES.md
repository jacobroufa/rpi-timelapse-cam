# Milestones

## v1.0 MVP (Shipped: 2026-02-17)

**Phases completed:** 3 phases, 9 plans, 0 tasks

**Key accomplishments:**
- Camera abstraction supporting Pi Camera (picamera2) and USB webcam (OpenCV) with auto-detection and failover
- Capture daemon with drift-corrected interval loop, exponential backoff recovery, and SIGHUP config reload
- Dual-threshold disk space management (warn 85%, stop 90%) with optional age-based cleanup
- Flask web UI with timeline filmstrip, keyboard navigation, auto-refreshing latest image, and PAM-authenticated daemon control
- Timelapse video generation via FFmpeg concat demuxer with auto-subsampling at 30fps cap and progress bar
- Full systemd integration with two services (capture + web), setup script, and sudoers config

**Stats:** 3 phases, 9 plans | 39 files, 4,033 LOC (Python + JS + HTML + CSS) | 1 day

---

