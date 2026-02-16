# Requirements: RPi Timelapse Cam

**Defined:** 2026-02-16
**Core Value:** Capture images reliably on a configurable interval and make them easy to browse and turn into timelapse videos -- all self-contained on a Raspberry Pi.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Capture

- [ ] **CAP-01**: Camera auto-detects Pi Camera (picamera2/libcamera) or USB webcam (OpenCV/v4l2) at startup
- [ ] **CAP-02**: Camera source is configurable (auto, picamera, usb) via YAML config
- [ ] **CAP-03**: Images captured at configurable interval (default 30 seconds)
- [ ] **CAP-04**: Images saved with ISO 8601 timestamps in date-organized directories (YYYY/MM/DD/HHMMSS.jpg)
- [ ] **CAP-05**: Capture daemon runs as a systemd service with auto-start and restart-on-crash
- [ ] **CAP-06**: All settings stored in a single YAML configuration file
- [ ] **CAP-07**: JPEG quality is configurable (trade storage for image quality)
- [ ] **CAP-08**: Storage output directory is configurable (SD card, USB drive, NAS mount)
- [ ] **CAP-09**: Capture subprocess uses timeouts to prevent hangs (max 30s per capture)
- [ ] **CAP-10**: Camera lock file prevents simultaneous access between daemon and web server

### Web UI

- [ ] **WEB-01**: Flask web server serves a tabbed interface (Timeline / Live View)
- [ ] **WEB-02**: Live View tab shows an auto-refreshing still image (ephemeral, no storage impact)
- [ ] **WEB-03**: Timeline tab displays a scrollable horizontal strip of captured images
- [ ] **WEB-04**: Thumbnails generated at capture time for fast timeline browsing
- [ ] **WEB-05**: Date picker allows jumping to specific days in the timeline
- [ ] **WEB-06**: Disk space warning displays on web UI when free space drops below configurable threshold (default 15%)
- [ ] **WEB-07**: Capture health indicator shows daemon status and last capture time
- [ ] **WEB-08**: User can start/stop capture from the web UI
- [ ] **WEB-09**: Web server runs as a systemd service

### Timelapse

- [ ] **TL-01**: Standalone Python script generates timelapse video from captured images using FFmpeg
- [ ] **TL-02**: Default compression: 1 week of captures into 2-minute video
- [ ] **TL-03**: Input period and output duration are both configurable via CLI arguments
- [ ] **TL-04**: Script calculates correct FFmpeg framerate from input/output parameters
- [ ] **TL-05**: Script runs on the Pi or any machine where images and FFmpeg are available

### Storage

- [ ] **STR-01**: Optional auto-cleanup deletes images older than N days (configurable, off by default)
- [ ] **STR-02**: Disk space monitored with configurable warning threshold (default 15% free)
- [ ] **STR-03**: Pre-capture disk space check prevents writing when disk is critically full

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Web UI Enhancements

- **WEB-10**: Timelapse generation triggered and previewed from web UI
- **WEB-11**: System health dashboard (CPU temperature, uptime, memory usage)
- **WEB-12**: Responsive design optimized for mobile browsers

### Capture Enhancements

- **CAP-11**: Sunrise/sunset-aware scheduling (skip nighttime captures)
- **CAP-12**: Exposure/white balance presets (indoor-plant, outdoor-sunny, etc.)
- **CAP-13**: Image overlay with timestamp/metadata burned into captures

## Out of Scope

| Feature | Reason |
|---------|--------|
| MJPEG live streaming | CPU-intensive on Pi, auto-refresh still is lighter and sufficient |
| Motion detection | Turns timelapse tool into surveillance system; motionEye does this better |
| Cloud sync / remote access | Adds auth, networking complexity; local network only for v1 |
| Multi-camera simultaneous capture | Doubles complexity everywhere; one camera at a time via config |
| Mobile app | Web UI accessed via mobile browser is sufficient |
| Video recording / continuous capture | Different storage/encoding requirements; stills only |
| User authentication | Local network, personal use; complexity not justified |
| Database for image metadata | Filesystem with timestamps is the database; no sync bugs |
| Plugin / extension system | Premature abstraction; well-structured code is sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAP-01 | Phase 1 | Pending |
| CAP-02 | Phase 1 | Pending |
| CAP-03 | Phase 1 | Pending |
| CAP-04 | Phase 1 | Pending |
| CAP-05 | Phase 1 | Pending |
| CAP-06 | Phase 1 | Pending |
| CAP-07 | Phase 1 | Pending |
| CAP-08 | Phase 1 | Pending |
| CAP-09 | Phase 1 | Pending |
| CAP-10 | Phase 1 | Pending |
| WEB-01 | Phase 2 | Pending |
| WEB-02 | Phase 2 | Pending |
| WEB-03 | Phase 2 | Pending |
| WEB-04 | Phase 2 | Pending |
| WEB-05 | Phase 2 | Pending |
| WEB-06 | Phase 2 | Pending |
| WEB-07 | Phase 2 | Pending |
| WEB-08 | Phase 2 | Pending |
| WEB-09 | Phase 2 | Pending |
| TL-01 | Phase 3 | Pending |
| TL-02 | Phase 3 | Pending |
| TL-03 | Phase 3 | Pending |
| TL-04 | Phase 3 | Pending |
| TL-05 | Phase 3 | Pending |
| STR-01 | Phase 1 | Pending |
| STR-02 | Phase 1 | Pending |
| STR-03 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0

---
*Requirements defined: 2026-02-16*
*Last updated: 2026-02-16 after roadmap creation*
