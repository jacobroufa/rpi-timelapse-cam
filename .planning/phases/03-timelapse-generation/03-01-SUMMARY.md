---
phase: 03-timelapse-generation
plan: 01
subsystem: cli
tags: [ffmpeg, subprocess, argparse, timelapse, video, concat-demuxer, pillow]

# Dependency graph
requires:
  - phase: 01-capture-daemon-storage-management
    provides: Date-organized image directory structure (YYYY/MM/DD/HHMMSS.jpg)
  - phase: 02-web-ui-timeline-browser
    provides: Thumbnail images in thumbs/ subdirectories
provides:
  - "timelapse generate CLI subcommand for MP4 video generation from image date ranges"
  - "FFmpeg concat demuxer pipeline with progress bar and auto-subsampling"
  - "Duration and range parsers for flexible CLI input"
  - "Resolution detection and mixed-resolution handling via scale+pad filter"
affects: []

# Tech tracking
tech-stack:
  added: [ffmpeg (external runtime dependency)]
  patterns: [concat demuxer file list, FFmpeg progress parsing, auto-subsampling FPS cap]

key-files:
  created: [src/timelapse/generate.py]
  modified: [src/timelapse/__main__.py, pyproject.toml]

key-decisions:
  - "30fps max cap with auto-subsampling (ceil(fps/max_fps) every_n) for broad player compatibility"
  - "Concat demuxer with temp file list and -safe 0 for absolute paths across date directories"
  - "FFmpeg -progress pipe:1 parsing for zero-dependency progress bar on stderr"
  - "Lazy PIL.Image.open for resolution detection (header only, no pixel decode)"
  - "Lazy import of generate module in CLI to avoid loading FFmpeg check at daemon startup"

patterns-established:
  - "Concat demuxer file list pattern: write temp .txt with file/duration pairs, repeat last entry"
  - "FPS auto-subsampling: when calculated fps > max_fps, compute every_n = ceil(fps/max_fps)"
  - "Custom argparse types for duration (90s, 2m, 1h30m) and range (7d, 2w, 1m) parsing"

requirements-completed: [TL-01, TL-02, TL-03, TL-04, TL-05]

# Metrics
duration: 3min
completed: 2026-02-17
---

# Phase 3 Plan 1: Timelapse Generation Summary

**FFmpeg concat demuxer pipeline with auto-subsampling FPS cap, progress bar, and full CLI subcommand for generating MP4 timelapses from date-organized image captures**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-17T03:52:12Z
- **Completed:** 2026-02-17T03:55:17Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Complete timelapse generation module (631 lines) with image collection, FPS calculation, FFmpeg command construction, progress bar, and full pipeline orchestration
- CLI subcommand `timelapse generate` with all 15 flags matching locked user decisions: --start, --end, --range, --duration, --images, --output, --thumbnails, --every, --sort, --resolution, --codec, --dry-run, --summary-only, --verbose, --silent
- Auto-subsampling when FPS exceeds 30: 10,080 images (1 week at 1/min) into 2-minute video yields 28fps with every-3rd-image sampling

## Task Commits

Each task was committed atomically:

1. **Task 1: Core timelapse generation module** - `40fb91e` (feat)
2. **Task 2: CLI subcommand and entry point wiring** - `2d905c0` (feat)

## Files Created/Modified
- `src/timelapse/generate.py` - Core timelapse generation: image collection, FPS calc, concat file, FFmpeg invocation, progress bar, duration/range parsers
- `src/timelapse/__main__.py` - Added `generate` subcommand with all CLI flags and `_run_generate` handler
- `pyproject.toml` - Added `timelapse-generate` console_scripts entry point

## Decisions Made
- Followed plan as specified. All implementation decisions (concat demuxer, progress parsing, sort options, resolution detection strategy, codec flag) aligned with RESEARCH.md recommendations and CONTEXT.md locked decisions.
- Lazy import of `timelapse.generate` in `_run_generate` and argparse setup to keep daemon startup fast (avoid loading Pillow/shutil.which at daemon import time)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. FFmpeg must be installed on the target system (the script provides platform-specific install instructions if missing).

## Next Phase Readiness
- This is the final phase of the project. All three phases are complete:
  - Phase 1: Capture daemon and storage management
  - Phase 2: Web UI and timeline browser
  - Phase 3: Timelapse video generation
- The project is feature-complete for v1.0

## Self-Check: PASSED

- FOUND: src/timelapse/generate.py
- FOUND: 03-01-SUMMARY.md
- FOUND: commit 40fb91e (Task 1)
- FOUND: commit 2d905c0 (Task 2)

---
*Phase: 03-timelapse-generation*
*Completed: 2026-02-17*
