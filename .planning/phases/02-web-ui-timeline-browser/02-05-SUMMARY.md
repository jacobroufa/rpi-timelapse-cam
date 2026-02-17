---
phase: 02-web-ui-timeline-browser
plan: 05
subsystem: ui
tags: [pam, flask-httpauth, systemctl, http-basic-auth, daemon-control, system-health]

# Dependency graph
requires:
  - phase: 02-web-ui-timeline-browser
    provides: "Flask app factory, health module, base template, control blueprint stub"
provides:
  - "PAM authentication module (auth.py) with HTTPBasicAuth + python-pam"
  - "Full control blueprint with start/stop/status endpoints"
  - "Control template with daemon buttons and system health dashboard"
  - "Interactive control.js with confirmation dialog and 5-second status polling"
affects: []

# Tech tracking
tech-stack:
  added: [python-pam, flask-httpauth]
  patterns: [pam-auth-via-http-basic, systemctl-subprocess, status-polling-js]

key-files:
  created:
    - src/timelapse/web/auth.py
    - src/timelapse/web/static/js/control.js
  modified:
    - src/timelapse/web/blueprints/control.py
    - src/timelapse/web/templates/control.html
    - src/timelapse/web/static/css/app.css

key-decisions:
  - "HTTP Basic Auth against PAM for single-tab auth -- browser caches credentials per session"
  - "Full /usr/bin/systemctl path in subprocess calls to match sudoers configuration"
  - "Dedicated Start/Stop buttons (not toggle) with confirm() on Stop only"
  - "5-second polling interval for status updates on Control tab"

patterns-established:
  - "PAM auth: auth.py module-level HTTPBasicAuth instance, imported by control blueprint"
  - "Service management: private helper functions wrapping subprocess.run with timeout"
  - "JSON endpoints: /control/start, /control/stop, /control/status for JS interaction"
  - "Health grid: 2-column CSS grid with article cards for system health dashboard"

requirements-completed: [WEB-08]

# Metrics
duration: 4min
completed: 2026-02-17
---

# Phase 2 Plan 5: Control Panel Summary

**PAM-authenticated Control tab with daemon start/stop via systemctl, confirmation on stop, and 4-card system health dashboard with 5-second polling**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-17T02:03:57Z
- **Completed:** 2026-02-17T02:07:30Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- PAM authentication module wrapping python-pam + Flask-HTTPAuth blocks unauthenticated access to all control routes
- Full control blueprint with start/stop/status JSON endpoints calling systemctl via sudo subprocess
- Control template with start/stop buttons, inline status messages, and 4-card system health dashboard (disk, capture stats, system info, config)
- Interactive JavaScript with confirmation dialog on stop, button state management, and 5-second status polling

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PAM auth module and control blueprint with systemctl integration** - `181dbaf` (feat)
2. **Task 2: Create control template and interactive JavaScript** - `69fb61e` (feat)

## Files Created/Modified
- `src/timelapse/web/auth.py` - PAM authentication wrapper with HTTPBasicAuth verify_password callback
- `src/timelapse/web/blueprints/control.py` - Full control blueprint with auth-protected routes for daemon management
- `src/timelapse/web/templates/control.html` - Control panel with daemon buttons, health grid, config summary
- `src/timelapse/web/static/js/control.js` - Start/stop handlers, confirm dialog, status polling every 5s
- `src/timelapse/web/static/css/app.css` - Control tab styles: service status colors, button styles, health grid layout

## Decisions Made
- HTTP Basic Auth against PAM (not sessions) -- browser caches credentials for tab lifetime, no server-side session storage needed
- Full /usr/bin/systemctl path in subprocess calls to match sudoers NOPASSWD configuration exactly
- Dedicated Start and Stop buttons (per user decision) with confirm() prompt only on Stop
- 5-second polling interval balances freshness with low overhead on Raspberry Pi
- Health dashboard uses Pico CSS article elements in a 2-column responsive grid

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Task 1 files (auth.py, control.py) were found already committed in a previous execution (commit 181dbaf from a prior plan run). The files were verified identical to the plan specification, so Task 1 commit references the existing commit rather than creating a duplicate.

## User Setup Required

None - no external service configuration required. PAM authentication uses existing Linux system credentials. Sudoers NOPASSWD rules for systemctl are documented in Phase 2 research and should be configured during deployment.

## Next Phase Readiness
- Phase 2 is now complete: all 5 plans executed (timeline, latest image, control)
- All three tabs are fully functional with their respective features
- The web UI is ready for Phase 3 (video generation) integration

## Self-Check: PASSED

All 5 created/modified files verified on disk. Both task commits (181dbaf, 69fb61e) confirmed in git history.

---
*Phase: 02-web-ui-timeline-browser*
*Plan: 05*
*Completed: 2026-02-17*
