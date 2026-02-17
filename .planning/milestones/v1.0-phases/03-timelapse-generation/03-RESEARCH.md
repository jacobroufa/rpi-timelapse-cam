# Phase 3: Timelapse Generation - Research

**Researched:** 2026-02-16
**Domain:** FFmpeg-based timelapse video generation from image sequences via Python CLI
**Confidence:** HIGH

## Summary

Phase 3 builds a standalone Python CLI script that takes a date range of captured images and generates a timelapse video using FFmpeg. The script has no dependency on the capture daemon or web server -- it reads the same date-organized directory structure (YYYY/MM/DD/HHMMSS.jpg) and calls FFmpeg as a subprocess. The core technical challenge is straightforward: enumerate images in a date range, calculate the correct framerate to hit a target video duration, construct an FFmpeg command, and provide progress feedback.

The recommended approach uses FFmpeg's **concat demuxer** with a generated file list rather than `-pattern_type glob` or `%d` sequential naming. The concat demuxer is the most robust choice for this project because: (1) filenames are timestamp-based (HHMMSS.jpg), not sequential numbers; (2) images span multiple date directories; (3) it works on all platforms including Windows; (4) the file list gives explicit control over which images are included and their order. The script generates a temporary text file listing all selected images with a uniform `duration` per frame (calculated from total images / target duration), then passes it to FFmpeg with `-f concat`.

For progress reporting, the recommended approach is to parse FFmpeg's native `-progress pipe:1` output, which emits machine-readable `key=value` pairs including `frame=N` on a configurable interval. This avoids adding a dependency (tqdm, rich, better-ffmpeg-progress) for what amounts to simple line parsing. The script reads `frame=` lines from FFmpeg's stdout and renders a simple progress bar to stderr using built-in string formatting. For users who want silence (--summary-only) or detail (--verbose), the same progress stream is simply displayed differently or suppressed.

**Primary recommendation:** Use subprocess + concat demuxer file list + FFmpeg `-progress pipe:1` parsing for a zero-extra-dependency CLI tool that feels like a simple Unix utility.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### CLI interface
- Three date flags: --start (required), --end, --range
- --end and --range are mutually exclusive; one is required alongside --start
- --range accepts N followed by d/w/m (days/weeks/months) relative to --start date
- --duration with unit suffixes (e.g. 2m, 90s) for target video duration
- Config-aware: reads output_dir from YAML config (same fallback chain as daemon), --images flag overrides
- Output defaults to current working directory, --output flag overrides
- --dry-run flag shows image count, calculated FPS, estimated duration, output path, then exits

#### Video output
- Default codec: H.264 MP4, with a flag to override codec/format
- Resolution matches source images by default, --resolution flag to override
- Default filename: timelapse_START_END.mp4 (e.g. timelapse_2026-01-01_2026-01-07.mp4)

#### Progress & errors
- Default: progress bar during encoding + summary line at end
- --summary-only flag for quiet mode (no progress bar, just final summary)
- --verbose flag for detailed output (image count, FFmpeg output, timing)
- Gaps in captures: warn about missing days by default, proceed anyway
- --silent flag suppresses gap warnings
- Zero images in range: error with clear message ("No images found for X to Y in /path") and non-zero exit
- Check FFmpeg is on PATH upfront before doing any work; clear install instructions in error message

#### Image selection
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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TL-01 | Standalone Python script generates timelapse video from captured images using FFmpeg | Concat demuxer approach with subprocess; `shutil.which("ffmpeg")` pre-check; zero extra Python dependencies beyond what the project already uses |
| TL-02 | Default compression: 1 week of captures into 2-minute video | FPS calculation: `fps = total_images / target_seconds`. At 1 capture/minute for 7 days = 10,080 images / 120 seconds = 84 fps. Capped at reasonable max (e.g., 60fps), excess images subsampled with --every |
| TL-03 | Input period and output duration are both configurable via CLI arguments | argparse with --start/--end/--range for input period, --duration with custom type parser for "2m"/"90s" suffixes |
| TL-04 | Script calculates correct FFmpeg framerate from input/output parameters | `fps = len(selected_images) / target_duration_seconds`; passed to FFmpeg via `-framerate` on concat demuxer input and `-r` on output |
| TL-05 | Script runs on the Pi or any machine where images and FFmpeg are available | No Pi-specific dependencies; pure stdlib + existing project config module; FFmpeg available via system package manager on all platforms |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess (stdlib) | Python 3.11+ | Run FFmpeg process | Zero dependency; full control over FFmpeg flags and progress parsing |
| argparse (stdlib) | Python 3.11+ | CLI argument parsing | Already used in project's __main__.py; no reason to add click/typer for a single script |
| pathlib (stdlib) | Python 3.11+ | File/directory traversal | Already used throughout project; consistent with existing storage patterns |
| shutil (stdlib) | Python 3.11+ | `shutil.which()` for FFmpeg detection | Standard way to check if binary is on PATH |
| tempfile (stdlib) | Python 3.11+ | Temporary concat file list | Auto-cleanup of the image list file passed to FFmpeg |
| timelapse.config | project | YAML config loading | Reuse existing config module for output_dir resolution |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PIL/Pillow | >=12.0 (already installed) | Read image dimensions for resolution detection | Only when --resolution not specified and images have mixed sizes |
| datetime (stdlib) | Python 3.11+ | Date range calculation, --range parsing | Core to date flag handling |
| re (stdlib) | Python 3.11+ | Parse --duration and --range suffixes | Custom argparse type functions |

### External Runtime Dependency
| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| FFmpeg | >=4.3 | Video encoding | `sudo apt install ffmpeg` (Debian/Ubuntu/Raspberry Pi OS), `brew install ffmpeg` (macOS), `choco install ffmpeg` (Windows) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| subprocess + concat demuxer | ffmpeg-python (kkroening) | Adds a dependency; project is unmaintained (last release 2019); subprocess is simpler for this use case |
| subprocess + concat demuxer | moviepy | Heavy dependency (numpy, imageio); overkill for "call FFmpeg with a file list" |
| Custom progress bar | tqdm | Adds a dependency for ~15 lines of code; project philosophy is minimal dependencies |
| Custom progress bar | better-ffmpeg-progress | Adds a dependency + Rich/tqdm transitive dep; overkill when parsing `-progress pipe:1` is straightforward |
| Concat demuxer file list | `-pattern_type glob` | Glob doesn't work on Windows; can't span multiple directories; "argument list too long" risk with thousands of images |
| Concat demuxer file list | `-framerate N -i img_%d.jpg` | Requires sequential numbered filenames; project uses HHMMSS.jpg naming across date dirs |

**Installation:**
```bash
# No new Python packages needed -- all stdlib + existing project deps
# FFmpeg is the only external requirement:
sudo apt install ffmpeg  # Raspberry Pi OS / Debian / Ubuntu
```

## Architecture Patterns

### Recommended Project Structure
```
src/timelapse/
    generate.py          # Core timelapse generation logic (image collection, FPS calc, FFmpeg command)
scripts/
    generate-timelapse   # CLI entry point (thin wrapper: argparse -> generate.py)
```

The script lives in `scripts/` as a standalone executable (like the existing `scripts/setup.sh`), with the core logic in `src/timelapse/generate.py` so it can be imported and tested independently. The script is also registered as a console_scripts entry point in pyproject.toml.

### Pattern 1: Concat Demuxer File List Generation
**What:** Generate a temporary text file listing all images with uniform duration, then pass to FFmpeg
**When to use:** Always -- this is the primary FFmpeg input method
**Example:**
```python
# Source: FFmpeg documentation + verified web sources
import tempfile
from pathlib import Path

def write_concat_file(image_paths: list[Path], fps: float) -> Path:
    """Write an FFmpeg concat demuxer file listing images with calculated duration."""
    duration = 1.0 / fps
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="timelapse_"
    )
    for img in image_paths:
        # Absolute paths require -safe 0
        tmp.write(f"file '{img}'\n")
        tmp.write(f"duration {duration:.6f}\n")
    # Repeat last image (FFmpeg concat demuxer quirk -- last duration is ignored without this)
    if image_paths:
        tmp.write(f"file '{image_paths[-1]}'\n")
    tmp.close()
    return Path(tmp.name)
```

### Pattern 2: FPS Calculation from Image Count and Target Duration
**What:** Calculate the framerate needed to compress N images into T seconds of video
**When to use:** Core to TL-02 and TL-04
**Example:**
```python
def calculate_fps(image_count: int, target_seconds: float) -> float:
    """Calculate FPS to fit image_count images into target_seconds of video.

    Returns a float FPS value. Caller should handle edge cases:
    - If fps > 60, suggest using --every to subsample
    - If fps < 1, warn about very slow playback
    """
    if target_seconds <= 0 or image_count <= 0:
        raise ValueError("Both image count and duration must be positive")
    return image_count / target_seconds
```

### Pattern 3: FFmpeg Command Construction with Progress Parsing
**What:** Build the FFmpeg command with concat input, codec settings, and progress output
**When to use:** Core encoding step
**Example:**
```python
import subprocess
import shutil

def build_ffmpeg_cmd(
    concat_file: Path,
    output_path: Path,
    fps: float,
    resolution: tuple[int, int] | None = None,
    codec: str = "libx264",
) -> list[str]:
    """Build FFmpeg command for timelapse encoding."""
    cmd = [
        shutil.which("ffmpeg") or "ffmpeg",
        "-y",  # Overwrite output without asking
        "-f", "concat",
        "-safe", "0",  # Allow absolute paths in concat file
        "-i", str(concat_file),
        "-c:v", codec,
        "-pix_fmt", "yuv420p",  # Maximum player compatibility
        "-r", str(int(min(fps, 60))),  # Output framerate, capped at 60
        "-progress", "pipe:1",  # Machine-readable progress to stdout
        "-nostats",  # Suppress default stderr stats (we parse stdout instead)
    ]
    if resolution:
        w, h = resolution
        # Scale + pad to handle aspect ratio mismatches
        cmd.extend([
            "-vf",
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
        ])
    cmd.append(str(output_path))
    return cmd
```

### Pattern 4: Progress Parsing from FFmpeg stdout
**What:** Read FFmpeg's `-progress pipe:1` key=value output to drive a progress bar
**When to use:** During encoding, unless --summary-only is set
**Example:**
```python
import subprocess
import sys

def run_ffmpeg_with_progress(cmd: list[str], total_frames: int) -> None:
    """Run FFmpeg command and display progress bar on stderr."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,  # Capture FFmpeg's own output
        text=True,
    )
    current_frame = 0
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("frame="):
            try:
                current_frame = int(line.split("=", 1)[1])
            except (ValueError, IndexError):
                continue
            pct = min(100, int(current_frame / total_frames * 100))
            bar_len = 40
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "-" * (bar_len - filled)
            print(f"\r[{bar}] {pct}% ({current_frame}/{total_frames} frames)",
                  end="", file=sys.stderr, flush=True)
        elif line == "progress=end":
            break
    proc.wait()
    print(file=sys.stderr)  # Newline after progress bar
    if proc.returncode != 0:
        stderr_output = proc.stderr.read()
        raise RuntimeError(f"FFmpeg failed (exit {proc.returncode}):\n{stderr_output}")
```

### Pattern 5: Image Collection Across Date Directories
**What:** Walk the date-organized directory tree to collect images in a date range
**When to use:** Core image discovery step
**Example:**
```python
from datetime import date, timedelta
from pathlib import Path

def collect_images(
    base_dir: Path,
    start: date,
    end: date,
    use_thumbnails: bool = False,
    every_n: int = 1,
) -> list[Path]:
    """Collect image paths from date-organized directories.

    Directory structure: base_dir/YYYY/MM/DD/HHMMSS.jpg
    Thumbnails:          base_dir/YYYY/MM/DD/thumbs/HHMMSS.jpg
    """
    images = []
    current = start
    while current <= end:
        day_dir = (
            base_dir
            / current.strftime("%Y")
            / current.strftime("%m")
            / current.strftime("%d")
        )
        if use_thumbnails:
            day_dir = day_dir / "thumbs"
        if day_dir.is_dir():
            day_images = sorted(day_dir.glob("*.jpg"))
            images.extend(day_images)
        current += timedelta(days=1)
    # Apply --every N subsampling
    if every_n > 1:
        images = images[::every_n]
    return images
```

### Anti-Patterns to Avoid
- **Piping raw image data to FFmpeg stdin (image2pipe):** Complex, error-prone, no advantage over concat file list for disk-resident images. The concat demuxer is simpler and lets FFmpeg handle file I/O directly.
- **Using ffmpeg-python or moviepy wrapper libraries:** Adds dependencies for no benefit when the FFmpeg command is well-understood and static. Direct subprocess gives full control and no abstraction leaks.
- **Calculating FPS and ignoring edge cases:** An FPS > 60 is impractical (most players cap at 60); an FPS < 1 means the video plays in slow motion. The script must handle both with clear warnings or automatic --every adjustment.
- **Hardcoding FFmpeg path:** Always use `shutil.which("ffmpeg")` to locate the binary; it handles PATH correctly on all platforms.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Video encoding | Custom pixel manipulation / frame-by-frame writing | FFmpeg via subprocess | FFmpeg handles codec negotiation, pixel format conversion, container muxing, and hardware acceleration; reimplementing any of this is futile |
| Image dimension detection | Manual JPEG header parsing | Pillow's `Image.open(path).size` (lazy, doesn't decode pixels) | JPEG, PNG, and other formats have complex header structures; Pillow already handles all of them |
| Config loading & path resolution | Separate config parser for the script | Existing `timelapse.config.load_config()` + `_resolve_config()` from `__main__.py` | Reuse the project's established config fallback chain; extract `_resolve_config` to a shared location |
| Date arithmetic | Manual day counting / calendar math | `datetime.date`, `datetime.timedelta`, `calendar.monthrange` | Leap years, month boundaries, etc. are already handled by stdlib |
| Resolution scaling / letterboxing | PIL-based frame-by-frame resize before FFmpeg | FFmpeg's `scale` + `pad` video filters | FFmpeg applies these filters in the encoding pipeline without creating intermediate files |

**Key insight:** This script is a thin orchestration layer between Python's stdlib (file discovery, argument parsing, date math) and FFmpeg (video encoding). Almost zero of the "hard" work should be in Python.

## Common Pitfalls

### Pitfall 1: Concat Demuxer Last-Duration Bug
**What goes wrong:** The last image in a concat file list has its duration ignored by FFmpeg, resulting in the video being slightly shorter than expected.
**Why it happens:** FFmpeg's concat demuxer uses `duration` to set how long to show each file, but the last entry's duration is not applied.
**How to avoid:** Repeat the last image entry at the end of the concat file (without a duration line). This is a well-documented workaround.
**Warning signs:** Video is slightly shorter than target duration; last image flashes by.

### Pitfall 2: FPS Exceeding Player/Encoder Limits
**What goes wrong:** With 10,080 images (1 week at 1/minute) and a 2-minute target, calculated FPS is 84, which exceeds common player capabilities and may cause encoding issues.
**Why it happens:** The FPS calculation is mathematically correct but practically unbounded.
**How to avoid:** Cap output FPS at 60 (or 30 for broader compatibility). When calculated FPS exceeds the cap, automatically subsample images. For example: 10,080 images at 60fps needs 120 seconds, which matches the 2-minute target. At 30fps, use every 2nd image (5,040 images / 30fps = 168 seconds ~2.8 minutes, or subsample more aggressively). The simplest approach: if `fps > max_fps`, compute `every_n = ceil(fps / max_fps)` and subsample.
**Warning signs:** FFmpeg warnings about framerate; video stuttering on playback.

### Pitfall 3: Absolute Paths in Concat File Without -safe 0
**What goes wrong:** FFmpeg refuses to read the concat file with "Unsafe file name" error.
**Why it happens:** FFmpeg's concat demuxer defaults to `-safe 1`, which rejects absolute paths and paths with special characters.
**How to avoid:** Always pass `-safe 0` when using the concat demuxer with absolute paths (which this project must, since images are in a configurable directory).
**Warning signs:** FFmpeg exits immediately with "unsafe" error before encoding starts.

### Pitfall 4: Missing `-pix_fmt yuv420p` Causes Playback Issues
**What goes wrong:** Generated video plays in FFmpeg/VLC but not in browsers, QuickTime, or mobile players.
**Why it happens:** Without explicit pixel format, FFmpeg may use yuv444p or other formats that many players don't support.
**How to avoid:** Always include `-pix_fmt yuv420p` in the encoding command.
**Warning signs:** Video plays in some players but shows black/green frames or refuses to play in others.

### Pitfall 5: Argparse Mutually Exclusive Group Limitations
**What goes wrong:** Attempting to create a nested mutually exclusive group for `(--end | --range)` while requiring one of them alongside `--start`.
**Why it happens:** Python's argparse does not support nested group logic like `--start AND (--end | --range)`. As of Python 3.14, nesting groups inside mutually exclusive groups raises an exception.
**How to avoid:** Use `add_mutually_exclusive_group(required=True)` for `--end` and `--range`, then validate `--start` is present in post-parse validation. Alternatively, make `--start` required via `required=True` on the argument itself.
**Warning signs:** Confusing help text; unexpected argument combinations accepted.

### Pitfall 6: FFmpeg Not Installed or Wrong Version
**What goes wrong:** Script starts collecting images and building the command, then fails at the encoding step.
**Why it happens:** FFmpeg is a system dependency, not a Python package. Users may not have it installed or may have an old version.
**How to avoid:** Check `shutil.which("ffmpeg")` at the very start of the script, before any image collection. If missing, print clear install instructions for the user's platform and exit with non-zero status.
**Warning signs:** `FileNotFoundError` from subprocess; no `ffmpeg` on PATH.

### Pitfall 7: Mixed Resolutions Causing FFmpeg Errors
**What goes wrong:** FFmpeg fails or produces garbled output when images have different resolutions.
**Why it happens:** The concat demuxer expects consistent frame dimensions. If images changed resolution (e.g., config change), frames will have different sizes.
**How to avoid:** Detect the minimum resolution across all selected images using `PIL.Image.open(path).size` (lazy, doesn't decode pixel data). Apply FFmpeg's `scale` + `pad` filter: `scale=W:H:force_original_aspect_ratio=decrease,pad=W:H:(ow-iw)/2:(oh-ih)/2` to fit all images into the smallest bounding box with letterboxing.
**Warning signs:** FFmpeg error about frame size mismatch; garbled/shifted frames in output.

## Code Examples

Verified patterns from official sources:

### FFmpeg Check on Startup
```python
# Source: Python docs (shutil.which), verified pattern
import shutil
import subprocess
import sys

def check_ffmpeg() -> str:
    """Verify FFmpeg is available and return its path.

    Raises SystemExit with install instructions if not found.
    """
    path = shutil.which("ffmpeg")
    if path is None:
        print(
            "FFmpeg is not installed or not on PATH.\n\n"
            "Install FFmpeg:\n"
            "  Raspberry Pi / Debian / Ubuntu:  sudo apt install ffmpeg\n"
            "  macOS (Homebrew):                 brew install ffmpeg\n"
            "  Windows (Chocolatey):             choco install ffmpeg\n"
            "  Windows (Scoop):                  scoop install ffmpeg\n",
            file=sys.stderr,
        )
        sys.exit(1)
    return path
```

### Duration String Parser (Custom argparse Type)
```python
# Source: standard argparse custom type pattern
import argparse
import re

def parse_duration(value: str) -> int:
    """Parse duration string like '2m', '90s', '1h30m' into total seconds."""
    pattern = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")
    match = pattern.fullmatch(value.strip())
    if not match or not any(match.groups()):
        raise argparse.ArgumentTypeError(
            f"Invalid duration: '{value}'. Use formats like '90s', '2m', '1h30m'."
        )
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    total = hours * 3600 + minutes * 60 + seconds
    if total <= 0:
        raise argparse.ArgumentTypeError("Duration must be greater than zero.")
    return total
```

### Range String Parser (Custom argparse Type)
```python
# Source: project-specific pattern for --range flag
import argparse
import re
from datetime import timedelta
from calendar import monthrange

def parse_range(value: str) -> str:
    """Validate range string like '7d', '2w', '1m'. Returns the raw string.

    Actual date calculation happens after --start is known.
    """
    pattern = re.compile(r"^(\d+)([dwm])$")
    match = pattern.fullmatch(value.strip())
    if not match:
        raise argparse.ArgumentTypeError(
            f"Invalid range: '{value}'. Use formats like '7d', '2w', '1m'."
        )
    return value

def range_to_end_date(start: "date", range_str: str) -> "date":
    """Convert a range string to an end date relative to start."""
    match = re.fullmatch(r"(\d+)([dwm])", range_str)
    n, unit = int(match.group(1)), match.group(2)
    if unit == "d":
        return start + timedelta(days=n - 1)  # inclusive
    elif unit == "w":
        return start + timedelta(weeks=n) - timedelta(days=1)
    elif unit == "m":
        # Add N months, handling month boundaries
        month = start.month + n
        year = start.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(start.day, monthrange(year, month)[1])
        return date(year, month, day) - timedelta(days=1)
```

### Resolution Detection Across Images
```python
# Source: Pillow docs (Image.open is lazy, only reads header)
from pathlib import Path
from PIL import Image

def detect_min_resolution(image_paths: list[Path]) -> tuple[int, int]:
    """Find the smallest resolution among a list of images.

    Uses Pillow's lazy open (reads header only, does not decode pixels).
    Returns (width, height) of the smallest bounding box.
    """
    min_w, min_h = float("inf"), float("inf")
    for path in image_paths:
        with Image.open(path) as im:
            w, h = im.size
            min_w = min(min_w, w)
            min_h = min(min_h, h)
    return (int(min_w), int(min_h))
```

### Gap Detection Between Date Ranges
```python
# Source: project-specific pattern
from datetime import date, timedelta
from pathlib import Path

def detect_gaps(
    base_dir: Path, start: date, end: date
) -> list[date]:
    """Find dates in the range that have no captured images."""
    missing = []
    current = start
    while current <= end:
        day_dir = (
            base_dir
            / current.strftime("%Y")
            / current.strftime("%m")
            / current.strftime("%d")
        )
        if not day_dir.is_dir() or not any(day_dir.glob("*.jpg")):
            missing.append(current)
        current += timedelta(days=1)
    return missing
```

## Discretion Recommendations

These are the areas marked as "Claude's Discretion" in CONTEXT.md, with researched recommendations:

### FFmpeg Command Construction: Concat Demuxer File List
**Recommendation:** Use the concat demuxer with a temporary file list (not piping, not glob, not sequential numbering).
**Rationale:** The project's HHMMSS.jpg naming across YYYY/MM/DD directories rules out `%d` patterns. Glob doesn't span directories and fails on Windows. The concat demuxer handles arbitrary file paths, works cross-platform, and gives explicit control over image order.

### Progress Bar: Custom FFmpeg Progress Parsing
**Recommendation:** Parse FFmpeg's `-progress pipe:1` output and render a simple `[####----] 45%` bar to stderr. No external dependency.
**Rationale:** Adding tqdm or rich for a progress bar in a CLI script that aims to "feel like a simple Unix tool" is inconsistent with the project's minimal-dependency philosophy. FFmpeg's progress output is well-documented and trivially parseable (read lines, match `frame=N`). The progress bar is ~15 lines of code.

### Sort Flag Options
**Recommendation:** `--sort` flag with choices: `filename` (default), `mtime`, `random`.
- `filename` -- default, alphabetical which equals chronological given HHMMSS.jpg naming
- `mtime` -- sort by file modification time, useful if filenames are unreliable
- `random` -- shuffle images for artistic effect
**Rationale:** `filename` covers the primary use case. `mtime` provides a fallback for edge cases. `random` adds creative value at zero implementation cost (just `random.shuffle()`).

### Scaling/Letterboxing Strategy
**Recommendation:** Scale to the smallest resolution found, with letterboxing (black bars) to preserve aspect ratio. Use FFmpeg's `scale=W:H:force_original_aspect_ratio=decrease,pad=W:H:(ow-iw)/2:(oh-ih)/2` filter.
**Rationale:** Scaling to smallest avoids upscaling artifacts. Letterboxing preserves framing vs. cropping which loses content. Black bars are the standard approach for mixed-resolution content. The user decision says "scale all images to match the smallest resolution found" -- letterboxing is the safest way to do this when aspect ratios differ.

### Codec Override Flag
**Recommendation:** `--codec` flag accepting FFmpeg encoder names directly (e.g., `libx264`, `libx265`, `h264_v4l2m2m`, `libsvtav1`).
**Rationale:** Passing the FFmpeg encoder name directly is the most flexible and least surprising approach. Users who know they want a specific codec already know the FFmpeg name. This avoids building a mapping layer. Default is `libx264` (universally available, good compression, fast encoding). On Pi 4, users can pass `--codec h264_v4l2m2m` for hardware-accelerated encoding (53-60fps vs 8-10fps for libx264 in software). Note: Pi 5 lacks a hardware H.264 encoder, so `libx264` is the only option there.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `h264_omx` for Pi hardware encoding | `h264_v4l2m2m` | RasPi OS Bullseye (2021) | OMX removed; v4l2m2m is the only hardware encoding path |
| ffmpeg-python (kkroening) | Direct subprocess | Library unmaintained since 2019 | No updates for 6+ years; subprocess is more reliable |
| `-pattern_type glob` for image input | Concat demuxer file list | Always available, but glob limitations widely known | File list is more portable and handles more edge cases |
| moviepy for video generation | Direct FFmpeg subprocess | moviepy 2.0 rewrite (2024) | moviepy is heavyweight and overkill for this use case |

**Deprecated/outdated:**
- `h264_omx`: Removed from Raspberry Pi OS Bullseye and later. Use `h264_v4l2m2m` for Pi 4 hardware encoding.
- `ffmpeg-python` (kkroening): Last release 0.2.0 in 2019. Effectively abandoned. Use subprocess directly.

## Open Questions

1. **Default FPS cap and auto-subsampling behavior**
   - What we know: 1 week at 1 capture/minute = 10,080 images. At 2-minute target = 84 fps, which exceeds 60fps.
   - What's unclear: Should the script automatically subsample to hit 30fps or 60fps? Or should it warn and let the user add --every?
   - Recommendation: Auto-subsample to stay at or below 30fps by default (maximizes player compatibility). Print a note when subsampling is applied. User can override with `--fps-cap 60` or similar.

2. **Entry point placement**
   - What we know: The project has `scripts/setup.sh` and `src/timelapse/__main__.py`. The timelapse script could be a subcommand of `timelapse` CLI or a separate `timelapse-generate` entry point.
   - What's unclear: Whether to add it as a subcommand (like `generate-thumbnails`) or as a separate script.
   - Recommendation: Add as a subcommand `timelapse generate [flags]` to keep a single entry point, consistent with the existing `generate-thumbnails` subcommand. Also register as a separate `timelapse-generate` console_scripts entry point for standalone use.

3. **Handling very large image sets (100k+ images)**
   - What we know: At 1 capture/minute for 3 months = ~130,000 images. The concat file list will be large but FFmpeg handles it.
   - What's unclear: Whether Pillow's lazy `Image.open()` for resolution detection is fast enough across 100k images.
   - Recommendation: Only check resolution on a sample (first, last, middle) unless `--resolution` is explicitly given. Log a warning if sampling detects a mismatch, then check all images.

## Sources

### Primary (HIGH confidence)
- FFmpeg official documentation (ffmpeg.org/ffmpeg.html) - `-progress` flag format, concat demuxer behavior
- FFmpeg formats documentation (ffmpeg.org/ffmpeg-formats.html) - concat demuxer file syntax, duration directive, `-safe` flag
- Python 3.11+ stdlib docs - argparse, subprocess, pathlib, shutil.which, tempfile
- Existing project source code - config.py, storage/manager.py, __main__.py, web/thumbnails.py

### Secondary (MEDIUM confidence)
- [Shotstack FFmpeg image-to-video guide](https://shotstack.io/learn/use-ffmpeg-to-convert-images-to-video/) - concat demuxer examples, glob vs file list tradeoffs
- [FFmpeg media image sequences article](https://www.ffmpeg.media/articles/image-sequences-timelapse-photos-to-video) - timelapse framerate settings, resolution handling
- [GitHub timelapse gist](https://gist.github.com/jkalucki/c81f8fe17599a8c9cd51b565d7dc27eb) - real-world FFmpeg timelapse command patterns
- [Raspberry Pi Forums h264_v4l2m2m](https://forums.raspberrypi.com/viewtopic.php?t=353958) - hardware encoding performance on Pi 3B/4
- [Gumlet FFmpeg scaling guide](https://www.gumlet.com/learn/ffmpeg-resize-video/) - force_original_aspect_ratio + pad filter pattern
- [tqdm PyPI](https://pypi.org/project/tqdm/) - version 4.67.3, Python >=3.7
- [better-ffmpeg-progress PyPI](https://pypi.org/project/better-ffmpeg-progress/) - FFmpeg progress wrapper library

### Tertiary (LOW confidence)
- [Raspberry Pi 5 hardware encoder limitations](https://mayaposch.wordpress.com/2024/04/08/the-tragicomedy-of-linux-raspberry-pi-and-hardware-accelerated-video-on-non-x86-platforms/) - Pi 5 lacks H.264 hardware encoder (needs validation on actual Pi 5 hardware)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib except Pillow (already installed); FFmpeg is universally available; patterns well-documented
- Architecture: HIGH - Concat demuxer + subprocess is the most commonly recommended approach across all sources; project structure follows existing patterns
- Pitfalls: HIGH - All pitfalls are well-documented in FFmpeg docs and community; concat demuxer quirks are widely known
- FPS calculation: HIGH - Simple arithmetic, verified against multiple timelapse guides
- Pi hardware encoding: MEDIUM - h264_v4l2m2m is confirmed for Pi 4 but Pi 5 limitation needs on-device validation

**Research date:** 2026-02-16
**Valid until:** 2026-03-16 (30 days - FFmpeg and Python stdlib are stable domains)
