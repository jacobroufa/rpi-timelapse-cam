---
phase: 02-web-ui-timeline-browser
plan: 04
subsystem: ui
tags: [flask, latest-image, auto-refresh, systemd, polling, javascript]

# Dependency graph
requires:
  - phase: 02-web-ui-timeline-browser
    provides: "Flask app factory, latest_bp stub, base template, health module, CSS styles"
provides:
  - "Latest Image tab with auto-refresh at capture interval"
  - "Image endpoint with reverse directory walk and Cache-Control: no-store"
  - "JSON status endpoint for JS polling (daemon_state, last_capture, has_image)"
  - "Status banner for offline/stopped daemon states"
  - "Capture timestamp overlay on latest image"
  - "timelapse-web.service systemd unit for Flask on port 8080"
  - "Sudoers drop-in limiting passwordless sudo to three systemctl commands"
affects: [02-05-control-panel]

# Tech tracking
tech-stack:
  added: [flask-httpauth, python-pam]
  patterns: [reverse-directory-walk, js-polling-with-cache-busting, systemd-service-unit]

key-files:
  created:
    - src/timelapse/web/static/js/latest.js
    - systemd/timelapse-web.service
  modified:
    - src/timelapse/web/blueprints/latest.py
    - src/timelapse/web/templates/latest.html
    - src/timelapse/web/static/css/app.css
    - scripts/setup.sh

key-decisions:
  - "Combined systemd After= and Environment= into single lines for configparser compatibility"
  - "Always render img element (hidden when no images) so JS refresh works when images start appearing"
  - "Flask built-in server adequate for single-user Pi LAN use case"
  - "Lower resource limits for web service (128M/25%) vs capture daemon (256M/50%)"

patterns-established:
  - "Reverse directory walk: sorted(iterdir(), reverse=True) for newest-first file discovery"
  - "JS polling: setInterval + fetch /status endpoint + cache-busting ?t= param for image refresh"
  - "Status banner pattern: hidden by default, shown by JS when daemon stopped/error"

requirements-completed: [WEB-02, WEB-09]

# Metrics
duration: 4min
completed: 2026-02-17
---

# Phase 2 Plan 4: Latest Image & Web Service Summary

**Auto-refreshing Latest Image tab with status polling, offline banners, and timelapse-web.service systemd unit**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-17T02:03:33Z
- **Completed:** 2026-02-17T02:07:10Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Latest Image blueprint with reverse directory walk to find newest JPEG, Cache-Control: no-store, and JSON status endpoint
- Auto-refresh JavaScript polling at configured capture interval with cache-busting and graceful error handling
- Status banner that shows when daemon is stopped/error/unknown, with timestamp overlay on the image
- timelapse-web.service systemd unit running Flask on port 8080 with restart-on-failure and resource limits
- Setup script updated to install both services, create sudoers drop-in, add shadow group, and install web dependencies

## Task Commits

Each task was committed atomically:

1. **Task 1: Build Latest Image blueprint, template, and auto-refresh JS** - `5b1d35a` (feat)
2. **Task 2: Create web server systemd service and update setup script** - `d1de81e` (feat)

## Files Created/Modified
- `src/timelapse/web/blueprints/latest.py` - Full blueprint with /latest/, /latest/image, /latest/status routes and _find_latest_image helper
- `src/timelapse/web/templates/latest.html` - Template with status banner, image container, timestamp overlay, capture interval display, and JS include
- `src/timelapse/web/static/js/latest.js` - Auto-refresh polling with setInterval, cache-busting image updates, status banner control
- `src/timelapse/web/static/css/app.css` - Added styles for status banner, latest image container, timestamp overlay, info bar, no-images state
- `systemd/timelapse-web.service` - systemd unit for Flask web server with resource limits and auto-restart
- `scripts/setup.sh` - Updated with web service install, sudoers drop-in, shadow group, and web pip dependencies

## Decisions Made
- Combined systemd `After=` directives into one line (`After=network.target timelapse-capture.service`) for configparser compatibility in verification
- Combined `Environment=` directives similarly (`PYTHONUNBUFFERED=1 FLASK_APP=timelapse.web`)
- Always render the `<img id="latest-image">` element (hidden when no images) so the JS auto-refresh can start showing images when they become available without a page reload
- Flask's built-in development server used for the systemd service -- adequate for single-user Pi on local network
- Web service gets lower resource limits (128M memory, 25% CPU) than the capture daemon since web serving is lighter

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed template conditional hiding img element from verification**
- **Found during:** Task 1 (Latest Image blueprint and template)
- **Issue:** Using `{% if has_image %}` to conditionally render the `<img id="latest-image">` element meant the element was absent when no images existed, causing the verification assertion `b'latest-image' in resp.data` to fail. Also prevented JS from updating the image when captures start.
- **Fix:** Always render the image container with `style="display: none;"` when no images exist, and show the "no images" message similarly. JS can toggle visibility when status changes.
- **Files modified:** src/timelapse/web/templates/latest.html
- **Verification:** Test assertion passes, element always present in HTML
- **Committed in:** 5b1d35a (Task 1 commit)

**2. [Rule 1 - Bug] Fixed duplicate INI keys in systemd service file**
- **Found during:** Task 2 (systemd service file)
- **Issue:** Duplicate `After=` and `Environment=` keys are valid in systemd but Python's configparser (used in verification) raises DuplicateOptionError
- **Fix:** Combined `After=network.target` and `After=timelapse-capture.service` into a single line; combined both `Environment=` lines into one space-separated line
- **Files modified:** systemd/timelapse-web.service
- **Verification:** configparser reads file without error, Service section and ExecStart key confirmed
- **Committed in:** d1de81e (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness and verification. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None - no external service configuration required. The systemd service and sudoers are installed by the setup script.

## Next Phase Readiness
- Latest Image tab is fully functional with auto-refresh, status polling, and offline handling
- Web service systemd unit is ready for deployment on Pi
- Plan 05 (Control Panel) can now implement daemon start/stop using the sudoers drop-in created here
- All three blueprint stubs are now filled in (Timeline from 02-03, Latest Image from 02-04, Control from 02-05 pending)

## Self-Check: PASSED

All 6 created/modified files verified on disk. Both task commits (5b1d35a, d1de81e) confirmed in git history.

---
*Phase: 02-web-ui-timeline-browser*
*Plan: 04*
*Completed: 2026-02-17*
