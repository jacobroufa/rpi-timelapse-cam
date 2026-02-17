# RPi Timelapse Cam

## What This Is

A three-part toolkit for Raspberry Pi that automates interval photography, provides a web interface for browsing captured images and monitoring system health, and generates timelapse videos from collected images using FFmpeg. Built for personal use — initially capturing plant growth, but designed to work with any subject.

## Core Value

Capture images reliably on a configurable interval and make them easy to browse and turn into timelapse videos — all self-contained on a Raspberry Pi.

## Requirements

### Validated

- ✓ Capture images at a configurable interval from Pi Camera or USB webcam — v1.0
- ✓ Serve a web UI on the Pi with tabbed navigation (Timeline / Latest Image / Control) — v1.0
- ✓ Timeline tab displays a scrollable horizontal filmstrip with keyboard navigation and date picker — v1.0
- ✓ Latest Image tab shows an auto-refreshing still image — v1.0
- ✓ Generate timelapse video from captured images via FFmpeg concat demuxer — v1.0
- ✓ Timelapse script compresses 1 week into 2 minutes by default, with configurable input/output durations — v1.0
- ✓ Timelapse script runs on the Pi or any machine where images and FFmpeg are available — v1.0
- ✓ Optional auto-cleanup: delete images older than N days (configurable, off by default) — v1.0
- ✓ Disk space warning on web UI when remaining space drops below threshold — v1.0
- ✓ Camera source is configurable (Pi Camera via picamera2, USB webcam via OpenCV) — v1.0

### Active

(None yet — define for next milestone)

### Out of Scope

- Mobile app — web UI accessed via browser is sufficient
- Cloud sync / remote access — local network only for v1
- MJPEG streaming — auto-refresh still is simpler and lighter on Pi resources
- Video recording — still images only, timelapse assembled from stills
- Multi-camera simultaneous capture — one camera source at a time

## Context

- Shipped v1.0 with 4,033 LOC across Python, JavaScript, HTML, CSS
- Tech stack: Python 3.11+, Flask, Pillow, PyYAML, picamera2, OpenCV, FFmpeg, Pico CSS
- Runs on Raspberry Pi (resource-constrained: limited CPU, RAM, storage)
- Camera hardware varies — supports Pi Camera Module (picamera2) and USB webcams (OpenCV/v4l2)
- Images stored locally on Pi's SD card or attached USB storage
- Web server accessed over local network by devices on the same WiFi
- FFmpeg available on Pi (via apt) and on desktop machines
- Initial use case: documenting plant growth over weeks/months

## Constraints

- **Hardware**: Must run comfortably on Raspberry Pi (low CPU/memory footprint)
- **Storage**: SD cards are limited — storage management is critical, auto-cleanup and warnings essential
- **Camera compatibility**: Abstract over picamera2 (Pi Camera) and OpenCV/v4l2 (USB webcam)
- **Portability**: FFmpeg timelapse script works standalone on any machine with FFmpeg installed
- **Network**: Web UI served on local network only; control tab requires PAM auth for daemon management

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Auto-refresh still for live view (not MJPEG stream) | Lower CPU/bandwidth on Pi, simpler implementation | ✓ Good — polling at capture interval is lightweight |
| Camera source abstraction (picamera2 + OpenCV) | Support both common Pi camera types without code changes | ✓ Good — lazy imports allow dev on any machine |
| Timelapse script as standalone FFmpeg wrapper | Runs anywhere, not coupled to the Pi or web server | ✓ Good — `--images` flag overrides config |
| No auth on browsing tabs, PAM auth on control tab | Local network use, but daemon control needs protection | ✓ Good — HTTP Basic + PAM is simple and effective |
| Config returns dict (not dataclass) | Easy SIGHUP reload without class reconstruction | ✓ Good — deep merge works naturally with dicts |
| Vendored Pico CSS | Pi may not have internet; offline operation required | ✓ Good — zero external CSS dependencies at runtime |
| Status file (.status.json) as integration layer | Daemon writes, web reads; no IPC coupling | ✓ Good — simple, reliable, debuggable |
| Flask built-in server for web service | Single-user Pi LAN use case; gunicorn/nginx overkill | ✓ Good — adequate for expected load |
| FFmpeg concat demuxer (not image sequence) | Handles non-contiguous date ranges and gaps naturally | ✓ Good — file list approach is most flexible |
| 30fps cap with auto-subsampling | Broad player compatibility per FFmpeg research | ✓ Good — prevents unplayable high-fps output |

---
*Last updated: 2026-02-17 after v1.0 milestone*
