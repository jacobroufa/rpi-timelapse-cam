# RPi Timelapse Cam

## What This Is

A three-part toolkit for Raspberry Pi that automates interval photography, provides a web interface for browsing captured images and viewing a live camera feed, and generates timelapse videos from collected images using FFmpeg. Built for personal use — initially capturing plant growth, but designed to work with any subject.

## Core Value

Capture images reliably on a configurable interval and make them easy to browse and turn into timelapse videos — all self-contained on a Raspberry Pi.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Capture images at a configurable interval (default 30 seconds) from Pi Camera or USB webcam
- [ ] Serve a web UI on the Pi with tabbed navigation (Timeline / Live View)
- [ ] Timeline tab displays a scrollable horizontal strip of captured images
- [ ] Live View tab shows an auto-refreshing still image (ephemeral — no storage impact)
- [ ] Generate timelapse video from captured images via FFmpeg script
- [ ] Timelapse script compresses 1 week into 2 minutes by default, with configurable input/output durations
- [ ] Timelapse script runs on the Pi or any machine where images are available
- [ ] Optional auto-cleanup: delete images older than N days (configurable, off by default)
- [ ] Disk space warning on web UI when remaining space drops below 15% (configurable threshold)
- [ ] Camera source is configurable (Pi Camera via libcamera, USB webcam via v4l2)

### Out of Scope

- Mobile app — web UI accessed via browser is sufficient
- Cloud sync / remote access — local network only for v1
- MJPEG streaming — auto-refresh still is simpler and lighter on Pi resources
- Video recording — still images only, timelapse assembled from stills
- Multi-camera simultaneous capture — one camera source at a time

## Context

- Runs on Raspberry Pi (resource-constrained: limited CPU, RAM, storage)
- Camera hardware varies — must support both Pi Camera Module (libcamera) and USB webcams (v4l2)
- Images stored locally on Pi's SD card or attached USB storage
- Web server accessed over local network by devices on the same WiFi
- FFmpeg available on Pi (via apt) and on desktop machines
- Initial use case: documenting plant growth over weeks/months

## Constraints

- **Hardware**: Must run comfortably on Raspberry Pi (low CPU/memory footprint)
- **Storage**: SD cards are limited — storage management is critical, auto-cleanup and warnings essential
- **Camera compatibility**: Must abstract over libcamera (Pi Camera) and v4l2 (USB webcam)
- **Portability**: FFmpeg timelapse script must work standalone on any machine with FFmpeg installed
- **Network**: Web UI served on local network only, no auth required for v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Auto-refresh still for live view (not MJPEG stream) | Lower CPU/bandwidth on Pi, simpler implementation | -- Pending |
| Camera source abstraction (libcamera + v4l2) | Support both common Pi camera types without code changes | -- Pending |
| Timelapse script as standalone FFmpeg wrapper | Runs anywhere, not coupled to the Pi or web server | -- Pending |
| No authentication on web UI | Local network only, personal use — complexity not justified | -- Pending |

---
*Last updated: 2026-02-16 after initialization*
