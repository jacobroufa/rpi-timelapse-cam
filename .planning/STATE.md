# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-16)

**Core value:** Capture images reliably on a configurable interval and make them easy to browse and turn into timelapse videos -- all self-contained on a Raspberry Pi.
**Current focus:** Phase 2: Web UI & Timeline Browser

## Current Position

Phase: 2 of 3 (Web UI & Timeline Browser)
Plan: 5 of 5 in current phase
Status: Phase 02 complete, all plans executed
Last activity: 2026-02-17 -- Completed 02-05-PLAN.md (Control Panel)

Progress: [######################] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: 3min
- Total execution time: 0.45 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-capture-daemon-storage-management | 3/3 | 10min | 3min |
| 02-web-ui-timeline-browser | 5/5 | 18min | 4min |

**Recent Trend:**
- Last 5 plans: 02-01 (2min), 02-02 (4min), 02-03 (4min), 02-04 (4min), 02-05 (4min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Config returns dict (not dataclass) for easy SIGHUP reload
- Deep merge allows partial user configs -- only override what you need
- Cleanup walks sorted directories so oldest days are processed first
- Output dir writability verified via touch/unlink test file
- Used capture_image() + PIL save for picamera2 JPEG quality (capture_file has no quality param)
- Lazy imports for picamera2 and cv2 so modules are importable on any machine
- Threaded timeout via daemon thread with join(timeout) for capture hang protection
- camera_lock yields None (not the file object) for cleaner context manager API
- Status file at output_dir/.status.json for co-location with images
- Sleep in 0.5s increments for responsive SIGTERM shutdown
- Backoff: min(5 * 2^failures + jitter, 300s) for camera recovery
- SIGHUP reloads interval/quality/thresholds but NOT source/resolution/output_dir
- Config fallback: --config > /etc/timelapse/ > ./config/
- Setup script does NOT auto-enable systemd service
- Thumbnails generated at capture time for fast timeline browsing
- Thumbnail failures wrapped in try/except to never crash daemon
- Backfill CLI uses sorted rglob to process images in date order
- Flask app factory pattern with blueprint-per-tab architecture
- Vendored Pico CSS for offline Pi operation
- Health indicators use hover popups for rich detail display
- Web config defaults: port 8080, host 0.0.0.0
- Context processor injects health dict into all templates
- HTTP Basic Auth against PAM for control tab -- browser caches credentials per session
- Full /usr/bin/systemctl path in subprocess calls to match sudoers config
- Dedicated Start/Stop buttons with confirm() on Stop only
- 5-second polling interval for control tab status updates

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-17
Stopped at: Completed 02-05-PLAN.md (Phase 02 complete)
Resume file: .planning/phases/02-web-ui-timeline-browser/02-05-SUMMARY.md
