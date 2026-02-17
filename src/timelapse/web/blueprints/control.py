"""Control tab blueprint.

Provides daemon start/stop controls and full system health display.
Plan 05 adds PAM authentication before any control content is visible.
"""

from flask import Blueprint, render_template

control_bp = Blueprint("control", __name__)


@control_bp.route("/")
def index():
    """Render the Control tab (no auth yet -- added in Plan 05)."""
    return render_template("control.html")
