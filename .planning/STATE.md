# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-16)

**Core value:** Capture images reliably on a configurable interval and make them easy to browse and turn into timelapse videos -- all self-contained on a Raspberry Pi.
**Current focus:** Phase 2: Web UI & Timeline Browser

## Current Position

Phase: 2 of 3 (Web UI & Timeline Browser)
Plan: 2 of 5 in current phase
Status: Plan 02-02 complete, continuing phase
Last activity: 2026-02-17 -- Completed 02-02-PLAN.md (Flask App Skeleton)

Progress: [################------] 62%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 3min
- Total execution time: 0.25 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-capture-daemon-storage-management | 3/3 | 10min | 3min |
| 02-web-ui-timeline-browser | 2/5 | 6min | 3min |

**Recent Trend:**
- Last 5 plans: 01-02 (3min), 01-03 (5min), 02-01 (2min), 02-02 (4min)
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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-17
Stopped at: Completed 02-02-PLAN.md
Resume file: .planning/phases/02-web-ui-timeline-browser/02-02-SUMMARY.md
