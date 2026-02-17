"""Flask application factory for the timelapse web UI.

Provides a three-tab interface (Timeline, Latest Image, Control) for browsing
captured timelapse images, viewing the latest capture, and managing the
capture daemon.
"""

from pathlib import Path

from flask import Flask


def create_app(config_path: Path | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_path: Path to the YAML config file. If None, uses the standard
            fallback chain: /etc/timelapse/timelapse.yml > ./config/timelapse.yml

    Returns:
        Configured Flask application with blueprints registered.
    """
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    # Load timelapse config (reuse Phase 1 config loader)
    from timelapse.config import load_config

    if config_path is None:
        config_path = _find_config()

    timelapse_cfg = load_config(config_path)

    app.config["TIMELAPSE"] = timelapse_cfg
    app.config["OUTPUT_DIR"] = Path(timelapse_cfg["storage"]["output_dir"])
    app.config["STATUS_FILE"] = app.config["OUTPUT_DIR"] / ".status.json"
    # Only used for flash messages; local network only
    app.config["SECRET_KEY"] = "timelapse-local-network"

    # Register blueprints
    from timelapse.web.blueprints.timeline import timeline_bp
    from timelapse.web.blueprints.latest import latest_bp
    from timelapse.web.blueprints.control import control_bp

    app.register_blueprint(timeline_bp)
    app.register_blueprint(latest_bp, url_prefix="/latest")
    app.register_blueprint(control_bp, url_prefix="/control")

    # Inject health data into all templates via context processor
    @app.context_processor
    def inject_health():
        from timelapse.web.health import get_health_summary

        return {
            "health": get_health_summary(
                app.config["STATUS_FILE"], timelapse_cfg
            )
        }

    return app


def _find_config() -> Path:
    """Config fallback chain matching the daemon's __main__.py.

    Searches:
        1. /etc/timelapse/timelapse.yml
        2. ./config/timelapse.yml

    Returns:
        Path to the first config file found.

    Raises:
        SystemExit: If no config file is found.
    """
    candidates = [
        Path("/etc/timelapse/timelapse.yml"),
        Path("./config/timelapse.yml"),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise SystemExit(
        "No config file found. Searched:\n"
        + "\n".join(f"  {i + 1}. {p}" for i, p in enumerate(candidates))
    )
