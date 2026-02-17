# Roadmap: RPi Timelapse Cam

## Overview

Three phases that each deliver one of the three independent components: capture daemon with storage management, web UI for browsing and monitoring, and timelapse video generation. The filesystem is the integration layer -- each phase produces or consumes images in date-organized directories. Phase 1 must complete first (nothing to display or encode without images), then Phase 2 (web UI) and Phase 3 (timelapse script) are independent but ordered by user value.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Capture Daemon & Storage Management** - Camera abstraction, interval capture, disk monitoring, cleanup, and systemd service (completed 2026-02-16)
- [ ] **Phase 2: Web UI & Timeline Browser** - Flask server with live view, timeline browsing, disk warnings, and capture control
- [ ] **Phase 3: Timelapse Generation** - Standalone FFmpeg script that compresses date ranges into configurable-duration videos

## Phase Details

### Phase 1: Capture Daemon & Storage Management
**Goal**: Images reliably accumulate on disk at a configurable interval, with storage managed to prevent disk-full failures
**Depends on**: Nothing (first phase)
**Requirements**: CAP-01, CAP-02, CAP-03, CAP-04, CAP-05, CAP-06, CAP-07, CAP-08, CAP-09, CAP-10, STR-01, STR-02, STR-03
**Success Criteria** (what must be TRUE):
  1. Daemon captures images from either a Pi Camera or USB webcam at the configured interval and saves them to date-organized directories (YYYY/MM/DD/HHMMSS.jpg)
  2. User can configure camera source, capture interval, JPEG quality, and storage location by editing a single YAML config file
  3. Daemon checks available disk space before each capture and refuses to write when storage is critically full
  4. When auto-cleanup is enabled, images older than the configured threshold are automatically deleted
  5. Daemon runs as a systemd service that starts on boot, restarts on crash, and recovers gracefully from camera disconnects
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md -- Project scaffolding, YAML config module, storage manager, and day-based cleanup
- [ ] 01-02-PLAN.md -- Camera abstraction layer: Pi Camera and USB backends, auto-detection, timeout, lock file
- [ ] 01-03-PLAN.md -- Capture daemon loop, CLI entry point, status reporting, systemd service, setup script

### Phase 2: Web UI & Timeline Browser
**Goal**: Users can browse captured images, see the latest capture, and monitor system health from any device on the local network
**Depends on**: Phase 1
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-06, WEB-07, WEB-08, WEB-09
**Success Criteria** (what must be TRUE):
  1. User can open the web UI in a browser and switch between Timeline, Latest Image, and Control tabs
  2. Latest Image tab shows an auto-refreshing still image from the most recent capture
  3. Timeline tab displays a scrollable horizontal filmstrip of thumbnail images with keyboard navigation and a date picker to jump to specific days
  4. Web UI shows a disk space warning when free storage drops below the configured threshold and displays capture daemon status with last capture time
  5. User can start and stop the capture daemon from the PAM-authenticated Control tab
**Plans**: 5 plans

Plans:
- [ ] 02-01-PLAN.md -- Thumbnail generation module, daemon integration, backfill CLI command
- [ ] 02-02-PLAN.md -- Flask app factory, base template with tabs and health indicators, Pico CSS styling
- [ ] 02-03-PLAN.md -- Timeline tab with filmstrip, keyboard navigation, date picker, image serving API
- [ ] 02-04-PLAN.md -- Latest Image tab with auto-refresh and systemd web service
- [ ] 02-05-PLAN.md -- Control tab with PAM authentication, daemon start/stop, system health dashboard

### Phase 3: Timelapse Generation
**Goal**: Users can turn any date range of captured images into a timelapse video with a single command
**Depends on**: Phase 1
**Requirements**: TL-01, TL-02, TL-03, TL-04, TL-05
**Success Criteria** (what must be TRUE):
  1. User can run a standalone script with a date range and output duration to generate a timelapse video
  2. By default, one week of captures compresses into a 2-minute video with the correct calculated framerate
  3. Script runs on the Pi or any machine where the images and FFmpeg are available, with no dependency on the capture daemon or web server
**Plans**: 1 plan

Plans:
- [ ] 03-01-PLAN.md -- Core timelapse generation module and CLI subcommand with FFmpeg concat demuxer

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Capture Daemon & Storage Management | 0/3 | Complete    | 2026-02-16 |
| 2. Web UI & Timeline Browser | 0/5 | Not started | - |
| 3. Timelapse Generation | 0/1 | Not started | - |
