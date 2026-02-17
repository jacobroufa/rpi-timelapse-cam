"""Timeline tab blueprint.

Displays the filmstrip timeline browser for navigating captured images
by date. Plan 03 replaces the placeholder with the full implementation.
"""

from flask import Blueprint, render_template

timeline_bp = Blueprint("timeline", __name__)


@timeline_bp.route("/")
def index():
    """Render the Timeline tab."""
    return render_template("timeline.html")
