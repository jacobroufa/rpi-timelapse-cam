"""Latest Image tab blueprint.

Displays the most recently captured image with auto-refresh.
Plan 04 replaces the placeholder with the full implementation.
"""

from flask import Blueprint, render_template

latest_bp = Blueprint("latest", __name__)


@latest_bp.route("/")
def index():
    """Render the Latest Image tab."""
    return render_template("latest.html")
