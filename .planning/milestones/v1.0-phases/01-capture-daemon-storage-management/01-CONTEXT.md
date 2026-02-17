# Phase 1: Capture Daemon & Storage Management - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

A background daemon that reliably captures images from a Pi Camera or USB webcam at a configurable interval, saves them to date-organized directories (YYYY/MM/DD/HHMMSS.jpg), manages disk space to prevent disk-full failures, and runs as a systemd service. Configuration via a single YAML file. Web UI and timelapse generation are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Capture cadence & recovery
- Default capture interval: 1 minute (configurable in YAML)
- Recovery from camera disconnect: Claude's discretion on retry/backoff strategy
- Failed capture logging: log to file if configured, otherwise skip silently (opt-in gap tracking)
- Config hot-reload vs restart: Claude's discretion based on complexity vs convenience

### Storage thresholds & cleanup
- Hard stop threshold: 90% disk usage — daemon refuses to write new captures
- Default retention period: 30 days (configurable in YAML)
- Auto-cleanup: off by default — user must explicitly enable in config
- Cleanup unit: oldest full days first — removes entire day directories to keep complete days intact

### Image quality & naming
- Default JPEG quality: 85% (configurable in YAML)
- Resolution: capture at native resolution up to 1080p, downscale if camera provides higher; configurable override in YAML
- Naming collisions: skip duplicate if a file already exists for that second
- Default storage path: ~/timelapse-images (configurable); setup script/docs should mention /var/lib/timelapse as an alternative for production installs

### Service & logging behavior
- Log verbosity: errors + camera connect/disconnect events (not every capture)
- Log destination: Claude's discretion (journal vs file vs both)
- Status file for external tools: Claude's discretion (JSON status file vs logs-only, considering Phase 2 web UI needs)
- Installation: setup script for quick install + thorough documentation so existing installations remain transparent and configurable

### Claude's Discretion
- Camera disconnect recovery strategy (retry timing, backoff)
- Config hot-reload vs restart-required
- Log destination (systemd journal, file, or both)
- Status reporting mechanism (JSON file vs systemd status vs other)
- Exact progress/status format

</decisions>

<specifics>
## Specific Ideas

- User wants gap tracking to be opt-in — default behavior should be silent on missed captures
- Cleanup should feel safe — removing full days keeps the directory structure clean and predictable
- Setup script should exist for quick onboarding, but the system should never feel opaque — heavy documentation so users understand and can manually configure everything
- Storage path default is user-friendly (~/timelapse-images) but docs should guide production users to /var/lib/timelapse

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-capture-daemon-storage-management*
*Context gathered: 2026-02-16*
