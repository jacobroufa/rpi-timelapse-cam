# Phase 3: Timelapse Generation - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Standalone CLI script that turns a date range of captured images into a timelapse video using FFmpeg. No dependency on the capture daemon or web server -- runs anywhere the images and FFmpeg are available.

</domain>

<decisions>
## Implementation Decisions

### CLI interface
- Three date flags: --start (required), --end, --range
- --end and --range are mutually exclusive; one is required alongside --start
- --range accepts N followed by d/w/m (days/weeks/months) relative to --start date
- --duration with unit suffixes (e.g. 2m, 90s) for target video duration
- Config-aware: reads output_dir from YAML config (same fallback chain as daemon), --images flag overrides
- Output defaults to current working directory, --output flag overrides
- --dry-run flag shows image count, calculated FPS, estimated duration, output path, then exits

### Video output
- Default codec: H.264 MP4, with a flag to override codec/format
- Resolution matches source images by default, --resolution flag to override
- Default filename: timelapse_START_END.mp4 (e.g. timelapse_2026-01-01_2026-01-07.mp4)

### Progress & errors
- Default: progress bar during encoding + summary line at end
- --summary-only flag for quiet mode (no progress bar, just final summary)
- --verbose flag for detailed output (image count, FFmpeg output, timing)
- Gaps in captures: warn about missing days by default, proceed anyway
- --silent flag suppresses gap warnings
- Zero images in range: error with clear message ("No images found for X to Y in /path") and non-zero exit
- Check FFmpeg is on PATH upfront before doing any work; clear install instructions in error message

### Image selection
- Default to full-size original images from date directories
- --thumbnails flag for quick/small preview timelapses
- --every N flag to use every Nth image (e.g. --every 2 uses every 2nd image)
- Resolution mismatches: scale all images to match the smallest resolution found
- Default sort by filename (HHMMSS.jpg naming = chronological), --sort flag with options to override

### Claude's Discretion
- FFmpeg command construction and pipe vs file-list approach
- Progress bar implementation (tqdm, custom, FFmpeg progress parsing)
- Exact --sort flag options beyond filename
- Scaling/letterboxing strategy for resolution mismatches
- Codec override flag name and accepted values

</decisions>

<specifics>
## Specific Ideas

- Script should feel like a simple Unix tool: sensible defaults, minimal required flags, composable
- --dry-run is important for users to verify before long encoding runs
- Must work on the Pi (ARM) and on any dev machine with FFmpeg -- no Pi-specific dependencies

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 03-timelapse-generation*
*Context gathered: 2026-02-16*
