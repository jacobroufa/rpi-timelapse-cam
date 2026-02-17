"""Timeline tab blueprint.

Serves the filmstrip timeline browser for navigating captured images by date.
Provides JSON API endpoints for listing available dates and images, plus
routes for serving full-size images and thumbnails (with on-demand fallback).
"""

import re
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

timeline_bp = Blueprint("timeline", __name__)


# ── Helpers ──────────────────────────────────────────────────────────────


def _list_available_dates(output_dir: Path) -> list[str]:
    """Walk YYYY/MM/DD directory structure, return sorted date strings.

    Only includes directories that contain at least one .jpg file
    (excluding the thumbs/ subdirectory).

    Returns:
        Sorted list of date strings in YYYY-MM-DD format.
    """
    dates: list[str] = []
    if not output_dir.is_dir():
        return dates

    for year_dir in sorted(output_dir.iterdir()):
        if not year_dir.is_dir() or not re.fullmatch(r"\d{4}", year_dir.name):
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir() or not re.fullmatch(r"\d{2}", month_dir.name):
                continue
            for day_dir in sorted(month_dir.iterdir()):
                if not day_dir.is_dir() or not re.fullmatch(r"\d{2}", day_dir.name):
                    continue
                # Check if day directory contains at least one .jpg
                has_jpg = any(
                    f.suffix.lower() == ".jpg"
                    for f in day_dir.iterdir()
                    if f.is_file()
                )
                if has_jpg:
                    dates.append(
                        f"{year_dir.name}-{month_dir.name}-{day_dir.name}"
                    )
    return dates


def _list_images_for_date(output_dir: Path, date_str: str) -> list[dict]:
    """List image metadata for a given date.

    Args:
        output_dir: Root output directory.
        date_str: Date in YYYY-MM-DD format (already validated).

    Returns:
        Sorted list of dicts with filename, thumb_url, full_url, time.
    """
    year, month, day = date_str.split("-")
    day_dir = output_dir / year / month / day

    if not day_dir.is_dir():
        return []

    images: list[dict] = []
    for f in sorted(day_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".jpg":
            continue
        # Skip thumbs directory entries (shouldn't be files, but guard anyway)
        if f.parent.name == "thumbs":
            continue

        # Derive time from filename (e.g., 143022.jpg -> 14:30:22)
        stem = f.stem
        if len(stem) >= 6 and stem[:6].isdigit():
            time_str = f"{stem[0:2]}:{stem[2:4]}:{stem[4:6]}"
        else:
            time_str = stem

        images.append(
            {
                "filename": f.name,
                "thumb_url": f"/thumb/{year}/{month}/{day}/{f.name}",
                "full_url": f"/image/{year}/{month}/{day}/{f.name}",
                "time": time_str,
            }
        )

    return images


def _validate_date(date_str: str) -> tuple[str, str, str] | None:
    """Validate a YYYY-MM-DD date string.

    Returns:
        Tuple of (year, month, day) strings if valid, None otherwise.
    """
    if not date_str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        return None
    year, month, day = date_str.split("-")
    # Basic range checks
    if not (1 <= int(month) <= 12 and 1 <= int(day) <= 31):
        return None
    return year, month, day


def _validate_path_component(value: str, pattern: str = r"\d+") -> bool:
    """Validate a URL path component is safe (digits only)."""
    return bool(re.fullmatch(pattern, value))


# ── Routes ───────────────────────────────────────────────────────────────


@timeline_bp.route("/")
def index():
    """Render the Timeline tab.

    Query params:
        date: YYYY-MM-DD to select. Defaults to most recent date with images.
    """
    output_dir = current_app.config["OUTPUT_DIR"]
    dates = _list_available_dates(output_dir)

    # Determine selected date
    selected_date = request.args.get("date", "")
    if selected_date not in dates:
        selected_date = dates[-1] if dates else ""

    # Get images for selected date
    images = _list_images_for_date(output_dir, selected_date) if selected_date else []

    return render_template(
        "timeline.html",
        dates=dates,
        selected_date=selected_date,
        images=images,
    )


@timeline_bp.route("/api/dates")
def api_dates():
    """Return JSON array of available date strings (YYYY-MM-DD), sorted ascending."""
    output_dir = current_app.config["OUTPUT_DIR"]
    dates = _list_available_dates(output_dir)
    return jsonify(dates)


@timeline_bp.route("/api/images/<date>")
def api_images(date: str):
    """Return JSON array of image objects for a given date.

    Each object has: filename, thumb_url, full_url, time.
    """
    if _validate_date(date) is None:
        abort(404)

    output_dir = current_app.config["OUTPUT_DIR"]
    images = _list_images_for_date(output_dir, date)
    return jsonify(images)


@timeline_bp.route("/image/<year>/<month>/<day>/<filename>")
def serve_image(year: str, month: str, day: str, filename: str):
    """Serve a full-size image from the output directory."""
    # Validate all path components
    if not (
        _validate_path_component(year, r"\d{4}")
        and _validate_path_component(month, r"\d{2}")
        and _validate_path_component(day, r"\d{2}")
        and re.fullmatch(r"[\w.-]+\.jpg", filename, re.IGNORECASE)
    ):
        abort(404)

    output_dir = current_app.config["OUTPUT_DIR"]
    image_dir = output_dir / year / month / day

    if not image_dir.is_dir():
        abort(404)

    return send_from_directory(image_dir, filename)


@timeline_bp.route("/thumb/<year>/<month>/<day>/<filename>")
def serve_thumb(year: str, month: str, day: str, filename: str):
    """Serve a thumbnail, generating on-demand if missing.

    Thumbnails are cached with max_age=86400 since they are immutable
    once generated.
    """
    # Validate all path components
    if not (
        _validate_path_component(year, r"\d{4}")
        and _validate_path_component(month, r"\d{2}")
        and _validate_path_component(day, r"\d{2}")
        and re.fullmatch(r"[\w.-]+\.jpg", filename, re.IGNORECASE)
    ):
        abort(404)

    output_dir = current_app.config["OUTPUT_DIR"]
    day_dir = output_dir / year / month / day
    thumb_dir = day_dir / "thumbs"

    # If thumbnail exists, serve it directly
    if (thumb_dir / filename).is_file():
        return send_from_directory(thumb_dir, filename, max_age=86400)

    # Fallback: generate on-demand if the full image exists
    full_image = day_dir / filename
    if not full_image.is_file():
        abort(404)

    # Generate thumbnail using the existing module
    from timelapse.web.thumbnails import generate_thumbnail

    try:
        generate_thumbnail(full_image, thumb_dir)
    except Exception:
        # If generation fails, 404 rather than crash
        abort(404)

    return send_from_directory(thumb_dir, filename, max_age=86400)
