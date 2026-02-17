---
phase: 02-web-ui-timeline-browser
plan: 02
subsystem: ui
tags: [flask, jinja2, pico-css, health-indicators, blueprints]

# Dependency graph
requires:
  - phase: 01-capture-daemon-storage-management
    provides: "config.py (load_config), status.py (read_status), .status.json format"
provides:
  - "Flask app factory (create_app) with three registered blueprints"
  - "Health module (get_health_summary, get_full_system_info)"
  - "Base template with tab navigation and health indicator bar"
  - "Pico CSS vendored for offline Pi use"
  - "CSS styles for filmstrip, thumbnails, health indicators"
  - "Web config defaults (port, host)"
affects: [02-03-timeline-filmstrip, 02-04-latest-image, 02-05-control-panel]

# Tech tracking
tech-stack:
  added: [flask, pico-css-v2, jinja2]
  patterns: [flask-app-factory, blueprint-registration, context-processor, hover-popup-health-indicators]

key-files:
  created:
    - src/timelapse/web/__init__.py
    - src/timelapse/web/health.py
    - src/timelapse/web/blueprints/__init__.py
    - src/timelapse/web/blueprints/timeline.py
    - src/timelapse/web/blueprints/latest.py
    - src/timelapse/web/blueprints/control.py
    - src/timelapse/web/templates/base.html
    - src/timelapse/web/templates/timeline.html
    - src/timelapse/web/templates/latest.html
    - src/timelapse/web/templates/control.html
    - src/timelapse/web/static/css/pico.min.css
    - src/timelapse/web/static/css/app.css
  modified:
    - src/timelapse/config.py
    - config/timelapse.yml

key-decisions:
  - "Hover popup instead of Pico data-tooltip for richer health detail display"
  - "Vendored Pico CSS for offline Pi operation"
  - "Web config defaults: port 8080, host 0.0.0.0"
  - "Health indicators use colored dots and hover popups with full system info"

patterns-established:
  - "Flask app factory: create_app(config_path) in web/__init__.py"
  - "Blueprint per tab: timeline (/), latest (/latest), control (/control)"
  - "Context processor injects health dict into all templates"
  - "CSS hover popup pattern for expandable health detail"

requirements-completed: [WEB-01, WEB-06, WEB-07]

# Metrics
duration: 4min
completed: 2026-02-16
---

# Phase 2 Plan 2: Flask App Skeleton Summary

**Three-tab Flask app with Pico CSS, health indicator bar with hover popups, and blueprint-per-tab architecture**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-17T01:56:10Z
- **Completed:** 2026-02-17T02:00:42Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Flask application factory with config loading, three blueprint registration, and health context processor
- Base template with responsive tab navigation (Timeline/Latest Image/Control) using Pico CSS
- Health indicator bar on all pages showing disk usage and daemon state with hover popups for full detail
- Vendored Pico CSS v2 for offline Raspberry Pi operation
- Custom CSS with filmstrip, thumbnail, and health indicator styles ready for Plan 03+

## Task Commits

Each task was committed atomically:

1. **Task 1: Flask app factory, health module, stub blueprints, and web config** - `6eb22fd` (feat)
2. **Task 2: Base template, tab templates, and static assets** - `c0c11af` (feat)

## Files Created/Modified
- `src/timelapse/web/__init__.py` - Flask app factory with create_app(), config loading, blueprint registration, health context processor
- `src/timelapse/web/health.py` - Health data aggregation from .status.json and system info
- `src/timelapse/web/blueprints/__init__.py` - Empty package init
- `src/timelapse/web/blueprints/timeline.py` - Timeline tab blueprint (stub, Plan 03 fills in)
- `src/timelapse/web/blueprints/latest.py` - Latest Image tab blueprint (stub, Plan 04 fills in)
- `src/timelapse/web/blueprints/control.py` - Control tab blueprint (stub, Plan 05 fills in)
- `src/timelapse/web/templates/base.html` - Base layout with tab nav, health bar, Pico CSS
- `src/timelapse/web/templates/timeline.html` - Timeline tab placeholder
- `src/timelapse/web/templates/latest.html` - Latest Image tab placeholder
- `src/timelapse/web/templates/control.html` - Control tab placeholder
- `src/timelapse/web/static/css/pico.min.css` - Vendored Pico CSS v2 (83KB)
- `src/timelapse/web/static/css/app.css` - Custom styles for health, filmstrip, thumbnails
- `src/timelapse/config.py` - Added web defaults (port 8080, host 0.0.0.0)
- `config/timelapse.yml` - Added commented-out web config section

## Decisions Made
- Used custom CSS hover popups instead of Pico's native data-tooltip for richer multi-line health detail display
- Vendored Pico CSS into static/css/ rather than CDN link for offline Pi operation
- Web config defaults set to port 8080 and host 0.0.0.0 for local network access
- Health indicators use small colored dots (green=running, red=error, orange=warning) with full info on hover
- Timeline blueprint registered at "/" so it serves as the home/default page

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Flask skeleton is fully functional with three tabs, health indicators, and placeholder content
- Plans 03-05 can extend the stub blueprints and templates with full implementations
- Filmstrip CSS styles are pre-defined for Plan 03's timeline implementation
- Health module provides data for both the base template indicators and the Control tab's full display

## Self-Check: PASSED

All 14 created/modified files verified on disk. Both task commits (6eb22fd, c0c11af) confirmed in git history.

---
*Phase: 02-web-ui-timeline-browser*
*Plan: 02*
*Completed: 2026-02-16*
