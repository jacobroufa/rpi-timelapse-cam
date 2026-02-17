"""Core timelapse video generation: image collection, FPS calculation, FFmpeg invocation, progress.

This module provides the full pipeline for generating timelapse videos from
date-organized image directories using FFmpeg's concat demuxer. No new
dependencies beyond stdlib + Pillow (already installed).
"""

import argparse
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from calendar import monthrange
from datetime import date, timedelta
from math import ceil
from pathlib import Path

from PIL import Image

from timelapse.config import load_config


# ---------------------------------------------------------------------------
# FFmpeg check
# ---------------------------------------------------------------------------

def check_ffmpeg() -> str:
    """Verify FFmpeg is available and return its path.

    Returns:
        Absolute path to the ffmpeg binary.

    Raises:
        SystemExit: If FFmpeg is not installed or not on PATH.
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


# ---------------------------------------------------------------------------
# Image collection
# ---------------------------------------------------------------------------

def collect_images(
    base_dir: Path,
    start: date,
    end: date,
    use_thumbnails: bool = False,
    every_n: int = 1,
    sort: str = "filename",
) -> list[Path]:
    """Collect image paths from date-organized directories.

    Directory structure: base_dir/YYYY/MM/DD/HHMMSS.jpg
    Thumbnails:          base_dir/YYYY/MM/DD/thumbs/HHMMSS.jpg

    Args:
        base_dir: Root image directory.
        start: First day to include (inclusive).
        end: Last day to include (inclusive).
        use_thumbnails: If True, look in thumbs/ subdirectories.
        every_n: Use every Nth image after sorting (1 = all).
        sort: Sort order -- "filename" (default, chronological), "mtime", or "random".

    Returns:
        List of Path objects for selected images.
    """
    images: list[Path] = []
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

    # Apply sort order
    if sort == "mtime":
        images.sort(key=lambda p: p.stat().st_mtime)
    elif sort == "random":
        random.shuffle(images)
    # "filename" is already sorted by the sorted() within each day

    # Apply every-N subsampling
    if every_n > 1:
        images = images[::every_n]

    return images


# ---------------------------------------------------------------------------
# Gap detection
# ---------------------------------------------------------------------------

def detect_gaps(base_dir: Path, start: date, end: date) -> list[date]:
    """Find dates in the range that have no captured images.

    Args:
        base_dir: Root image directory.
        start: First day of range (inclusive).
        end: Last day of range (inclusive).

    Returns:
        List of dates with no images.
    """
    missing: list[date] = []
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


# ---------------------------------------------------------------------------
# FPS calculation
# ---------------------------------------------------------------------------

def calculate_fps(
    image_count: int,
    target_seconds: float,
    max_fps: float = 30.0,
) -> tuple[float, int]:
    """Calculate FPS to fit image_count images into target_seconds of video.

    If the calculated FPS exceeds max_fps, auto-subsample: reduce the number
    of images so that the resulting FPS stays at or below max_fps.

    Args:
        image_count: Total number of images available.
        target_seconds: Desired video duration in seconds.
        max_fps: Maximum allowed FPS (default 30 for broad player compatibility).

    Returns:
        Tuple of (fps, every_n) where every_n is the subsampling interval.
        every_n == 1 means all images are used.

    Raises:
        ValueError: If image_count or target_seconds are not positive.
    """
    if target_seconds <= 0 or image_count <= 0:
        raise ValueError("Both image count and duration must be positive")

    fps = image_count / target_seconds
    every_n = 1

    if fps > max_fps:
        every_n = ceil(fps / max_fps)
        effective_count = len(range(0, image_count, every_n))
        fps = effective_count / target_seconds

    return (fps, every_n)


# ---------------------------------------------------------------------------
# Resolution detection
# ---------------------------------------------------------------------------

def detect_resolution(
    image_paths: list[Path],
    explicit: tuple[int, int] | None = None,
) -> tuple[int, int] | None:
    """Determine if a scaling filter is needed for the FFmpeg command.

    If explicit is given, return it directly. Otherwise sample first, middle,
    and last images. If all have the same size, return None (no filter needed).
    If sizes differ, scan all images and return the minimum width and height.

    Args:
        image_paths: List of image paths to check.
        explicit: User-specified resolution, or None.

    Returns:
        (width, height) if scaling is needed, or None if all images match.
    """
    if explicit is not None:
        return explicit

    if not image_paths:
        return None

    # Sample first, middle, last
    indices = {0, len(image_paths) // 2, len(image_paths) - 1}
    sizes = set()
    for idx in indices:
        with Image.open(image_paths[idx]) as im:
            sizes.add(im.size)

    if len(sizes) == 1:
        return None  # All sampled images have the same size -- no filter needed

    # Mixed sizes detected: scan all images for minimum bounding box
    min_w, min_h = float("inf"), float("inf")
    for path in image_paths:
        with Image.open(path) as im:
            w, h = im.size
            min_w = min(min_w, w)
            min_h = min(min_h, h)

    return (int(min_w), int(min_h))


# ---------------------------------------------------------------------------
# Concat file generation
# ---------------------------------------------------------------------------

def write_concat_file(image_paths: list[Path], fps: float) -> Path:
    """Write an FFmpeg concat demuxer file listing images with calculated duration.

    Each image gets a uniform duration of 1/fps seconds. The last image is
    repeated without a duration line as a workaround for the concat demuxer
    last-duration bug.

    Args:
        image_paths: Ordered list of image paths.
        fps: Frames per second (determines per-frame duration).

    Returns:
        Path to the generated temporary concat file.
    """
    duration = 1.0 / fps
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="timelapse_"
    )
    for img in image_paths:
        tmp.write(f"file '{img.resolve()}'\n")
        tmp.write(f"duration {duration:.6f}\n")
    # Repeat last image (concat demuxer quirk -- last duration is ignored)
    if image_paths:
        tmp.write(f"file '{image_paths[-1].resolve()}'\n")
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# FFmpeg command construction
# ---------------------------------------------------------------------------

def build_ffmpeg_cmd(
    ffmpeg_path: str,
    concat_file: Path,
    output_path: Path,
    fps: float,
    resolution: tuple[int, int] | None = None,
    codec: str = "libx264",
) -> list[str]:
    """Build the FFmpeg command list for timelapse encoding.

    Args:
        ffmpeg_path: Absolute path to the ffmpeg binary.
        concat_file: Path to the concat demuxer input file.
        output_path: Desired output video file path.
        fps: Output framerate (capped at 60).
        resolution: (width, height) for scaling, or None to skip.
        codec: FFmpeg video codec name (default: libx264).

    Returns:
        List of command-line arguments for subprocess.
    """
    cmd = [
        ffmpeg_path,
        "-y",  # Overwrite output without asking
        "-f", "concat",
        "-safe", "0",  # Allow absolute paths in concat file
        "-i", str(concat_file),
        "-c:v", codec,
        "-pix_fmt", "yuv420p",  # Maximum player compatibility
        "-r", str(int(min(fps, 60))),  # Output framerate, capped at 60
        "-progress", "pipe:1",  # Machine-readable progress to stdout
        "-nostats",  # Suppress default stderr stats
    ]
    if resolution is not None:
        w, h = resolution
        cmd.extend([
            "-vf",
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
        ])
    cmd.append(str(output_path))
    return cmd


# ---------------------------------------------------------------------------
# FFmpeg execution with progress
# ---------------------------------------------------------------------------

def run_ffmpeg(
    cmd: list[str],
    total_frames: int,
    show_progress: bool = True,
    verbose: bool = False,
) -> None:
    """Run FFmpeg and optionally display a progress bar on stderr.

    Args:
        cmd: FFmpeg command as a list of arguments.
        total_frames: Expected total number of frames for progress calculation.
        show_progress: If True, render a progress bar to stderr.
        verbose: If True, print FFmpeg's stderr output at the end.

    Raises:
        RuntimeError: If FFmpeg exits with a non-zero return code.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
            if show_progress and total_frames > 0:
                pct = min(100, int(current_frame / total_frames * 100))
                bar_len = 40
                filled = int(bar_len * pct / 100)
                bar = "#" * filled + "-" * (bar_len - filled)
                print(
                    f"\r[{bar}] {pct}% ({current_frame}/{total_frames} frames)",
                    end="",
                    file=sys.stderr,
                    flush=True,
                )
        elif line == "progress=end":
            break

    proc.wait()

    # Always print a newline after the progress bar
    if show_progress:
        print(file=sys.stderr)

    stderr_output = proc.stderr.read()

    if verbose and stderr_output:
        print("FFmpeg output:", file=sys.stderr)
        print(stderr_output, file=sys.stderr)

    if proc.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed (exit {proc.returncode}):\n{stderr_output}"
        )


# ---------------------------------------------------------------------------
# Duration parser
# ---------------------------------------------------------------------------

def parse_duration(value: str) -> int:
    """Parse a duration string like '2m', '90s', '1h30m' into total seconds.

    Custom argparse type function.

    Args:
        value: Duration string (e.g. "90s", "2m", "1h30m").

    Returns:
        Total duration in seconds.

    Raises:
        argparse.ArgumentTypeError: If the format is invalid.
    """
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


# ---------------------------------------------------------------------------
# Range parser
# ---------------------------------------------------------------------------

def parse_range(value: str) -> str:
    """Validate a range string like '7d', '2w', '1m'.

    Custom argparse type function. Returns the raw string -- actual date
    calculation happens after --start is known.

    Args:
        value: Range string (e.g. "7d", "2w", "1m").

    Returns:
        The validated raw string.

    Raises:
        argparse.ArgumentTypeError: If the format is invalid.
    """
    pattern = re.compile(r"^(\d+)([dwm])$")
    match = pattern.fullmatch(value.strip())
    if not match:
        raise argparse.ArgumentTypeError(
            f"Invalid range: '{value}'. Use formats like '7d', '2w', '1m'."
        )
    return value


def range_to_end_date(start: date, range_str: str) -> date:
    """Convert a range string to an end date relative to start.

    Args:
        start: The start date.
        range_str: Validated range string (e.g. "7d", "2w", "1m").

    Returns:
        The computed end date (inclusive).
    """
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
    else:
        raise ValueError(f"Unknown range unit: {unit}")


# ---------------------------------------------------------------------------
# Top-level generate function
# ---------------------------------------------------------------------------

def generate_timelapse(
    images_dir: Path,
    start: date,
    end: date,
    duration_seconds: int = 120,
    output_path: Path | None = None,
    use_thumbnails: bool = False,
    every_n: int = 1,
    sort: str = "filename",
    resolution: tuple[int, int] | None = None,
    codec: str = "libx264",
    dry_run: bool = False,
    show_progress: bool = True,
    verbose: bool = False,
    silent: bool = False,
) -> Path:
    """Orchestrate the full timelapse generation pipeline.

    Args:
        images_dir: Base directory containing date-organized images.
        start: First date to include (inclusive).
        end: Last date to include (inclusive).
        duration_seconds: Target video duration in seconds (default 120 = 2 min).
        output_path: Output video file path, or None for auto-generated name.
        use_thumbnails: If True, use thumbnail images instead of originals.
        every_n: Use every Nth image (1 = all).
        sort: Image sort order ("filename", "mtime", "random").
        resolution: Explicit output resolution (width, height), or None for auto.
        codec: FFmpeg video codec name.
        dry_run: If True, show what would be done without encoding.
        show_progress: If True, display a progress bar during encoding.
        verbose: If True, show detailed FFmpeg output.
        silent: If True, suppress gap warnings.

    Returns:
        Path to the output video file.

    Raises:
        SystemExit: If FFmpeg is missing or no images are found.
        RuntimeError: If FFmpeg encoding fails.
    """
    # 1. Check FFmpeg is available
    ffmpeg_path = check_ffmpeg()

    # 2. Collect images
    images = collect_images(
        base_dir=images_dir,
        start=start,
        end=end,
        use_thumbnails=use_thumbnails,
        every_n=every_n,
        sort=sort,
    )
    if not images:
        print(
            f"No images found for {start} to {end} in {images_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 3. Detect gaps and warn
    gaps = detect_gaps(images_dir, start, end)
    if gaps and not silent:
        gap_strs = [g.isoformat() for g in gaps]
        print(
            f"Warning: No images found for {len(gaps)} day(s): "
            + ", ".join(gap_strs),
            file=sys.stderr,
        )

    # 4. Calculate FPS (may auto-subsample)
    fps, auto_every = calculate_fps(len(images), duration_seconds)
    if auto_every > 1:
        if not silent:
            print(
                f"Note: Auto-subsampling every {auto_every} images to stay "
                f"at {fps:.1f} fps (original count: {len(images)})",
                file=sys.stderr,
            )
        images = images[::auto_every]
        # Recalculate fps with the subsampled count
        fps = len(images) / duration_seconds

    # 5. Detect resolution (scaling needed?)
    resolved_resolution = detect_resolution(images, resolution)

    # 6. Generate default output path if not given
    if output_path is None:
        output_path = Path(
            f"timelapse_{start.isoformat()}_{end.isoformat()}.mp4"
        )

    # 7. Dry run: print summary and return
    if dry_run:
        est_duration = len(images) / fps if fps > 0 else 0
        print(f"Images:   {len(images)}")
        print(f"FPS:      {fps:.1f}")
        print(f"Duration: {est_duration:.1f}s ({est_duration / 60:.1f}m)")
        print(f"Output:   {output_path}")
        if resolved_resolution:
            print(f"Scale to: {resolved_resolution[0]}x{resolved_resolution[1]}")
        return output_path

    # 8. Write concat file
    concat_file = write_concat_file(images, fps)

    try:
        # 9. Build FFmpeg command
        cmd = build_ffmpeg_cmd(
            ffmpeg_path=ffmpeg_path,
            concat_file=concat_file,
            output_path=output_path,
            fps=fps,
            resolution=resolved_resolution,
            codec=codec,
        )

        # 10. Run FFmpeg with progress
        run_ffmpeg(cmd, len(images), show_progress=show_progress, verbose=verbose)
    finally:
        # 11. Clean up temp concat file
        try:
            os.unlink(concat_file)
        except OSError:
            pass

    # 12. Print summary line
    file_size = output_path.stat().st_size
    size_mb = file_size / (1024 * 1024)
    est_duration = len(images) / fps if fps > 0 else 0

    # Try to get actual duration from ffprobe
    actual_duration_str = f"{est_duration:.1f}s (estimated)"
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        try:
            result = subprocess.run(
                [
                    ffprobe_path,
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                actual_secs = float(result.stdout.strip())
                actual_duration_str = f"{actual_secs:.1f}s ({actual_secs / 60:.1f}m)"
        except (subprocess.TimeoutExpired, ValueError, OSError):
            pass

    print(
        f"Output:   {output_path}\n"
        f"Size:     {size_mb:.1f} MB\n"
        f"Duration: {actual_duration_str}\n"
        f"Frames:   {len(images)} at {fps:.1f} fps"
    )

    # 13. Return output path
    return output_path
