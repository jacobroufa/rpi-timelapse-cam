"""Latest Image tab blueprint.

Displays the most recently captured image with auto-refresh at the
configured capture interval. Provides endpoints for the image itself,
and a JSON status endpoint for updating the status banner and timestamp
without a full page reload.
"""

from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, send_file

latest_bp = Blueprint("latest", __name__)


def _find_latest_image(output_dir: Path) -> Path | None:
    """Walk the output directory in reverse to find the newest JPEG.

    Directory structure: output_dir/YYYY/MM/DD/*.jpg
    Iterates year > month > day > file in reverse-sorted order so the
    first match is the most recent image.

    Args:
        output_dir: Root output directory containing year subdirectories.

    Returns:
        Path to the newest JPEG, or None if no images exist.
    """
    if not output_dir.is_dir():
        return None

    for year_dir in sorted(output_dir.iterdir(), reverse=True):
        if not year_dir.is_dir() or year_dir.name.startswith("."):
            continue
        for month_dir in sorted(year_dir.iterdir(), reverse=True):
            if not month_dir.is_dir():
                continue
            for day_dir in sorted(month_dir.iterdir(), reverse=True):
                if not day_dir.is_dir():
                    continue
                for entry in sorted(day_dir.iterdir(), reverse=True):
                    if entry.name == "thumbs" or entry.is_dir():
                        continue
                    if entry.suffix.lower() == ".jpg":
                        return entry
    return None


@latest_bp.route("/")
def index():
    """Render the Latest Image tab."""
    output_dir = current_app.config["OUTPUT_DIR"]
    capture_interval = current_app.config["TIMELAPSE"]["capture"]["interval"]
    has_image = _find_latest_image(output_dir) is not None

    return render_template(
        "latest.html",
        capture_interval=capture_interval,
        has_image=has_image,
    )


@latest_bp.route("/image")
def latest_image():
    """Serve the most recently captured JPEG.

    Returns the image with Cache-Control: no-store to prevent browser
    caching, ensuring each request gets the freshest image.
    """
    output_dir = current_app.config["OUTPUT_DIR"]
    image_path = _find_latest_image(output_dir)

    if image_path is None:
        return "No images captured yet", 404

    response = send_file(image_path, mimetype="image/jpeg")
    response.headers["Cache-Control"] = "no-store"
    return response


@latest_bp.route("/status")
def status():
    """Return JSON status for the JS polling endpoint.

    Returns:
        JSON with daemon_state, last_capture, and has_image fields.
    """
    from timelapse.web.health import get_health_summary

    output_dir = current_app.config["OUTPUT_DIR"]
    health = get_health_summary(
        current_app.config["STATUS_FILE"],
        current_app.config["TIMELAPSE"],
    )
    has_image = _find_latest_image(output_dir) is not None

    return jsonify({
        "daemon_state": health["daemon_state"],
        "last_capture": health["last_capture"],
        "has_image": has_image,
    })
