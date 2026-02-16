"""YAML configuration loading with validation and defaults."""

from pathlib import Path

import yaml


DEFAULTS = {
    "capture": {
        "interval": 60,
        "source": "auto",
        "jpeg_quality": 85,
        "resolution": [1920, 1080],
    },
    "storage": {
        "output_dir": "~/timelapse-images",
        "stop_threshold": 90,
        "warn_threshold": 85,
        "cleanup_enabled": False,
        "retention_days": 30,
    },
    "logging": {
        "gap_tracking": False,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge override into base. Returns a new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate(config: dict) -> None:
    """Validate configuration values. Raises SystemExit on invalid config."""
    capture = config.get("capture", {})
    storage = config.get("storage", {})

    interval = capture.get("interval")
    if not isinstance(interval, (int, float)) or interval <= 0:
        raise SystemExit(
            f"Invalid capture.interval: {interval!r} (must be a positive number)"
        )

    quality = capture.get("jpeg_quality")
    if not isinstance(quality, int) or not (1 <= quality <= 100):
        raise SystemExit(
            f"Invalid capture.jpeg_quality: {quality!r} (must be an integer 1-100)"
        )

    stop_threshold = storage.get("stop_threshold")
    if not isinstance(stop_threshold, (int, float)) or not (0 <= stop_threshold <= 100):
        raise SystemExit(
            f"Invalid storage.stop_threshold: {stop_threshold!r} (must be 0-100)"
        )

    warn_threshold = storage.get("warn_threshold")
    if not isinstance(warn_threshold, (int, float)) or not (0 <= warn_threshold <= 100):
        raise SystemExit(
            f"Invalid storage.warn_threshold: {warn_threshold!r} (must be 0-100)"
        )

    retention_days = storage.get("retention_days")
    if not isinstance(retention_days, (int, float)) or retention_days <= 0:
        raise SystemExit(
            f"Invalid storage.retention_days: {retention_days!r} (must be a positive number)"
        )


def load_config(config_path: Path) -> dict:
    """Load YAML configuration from disk, apply defaults, validate, and return.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        A dict with all configuration values, defaults applied for missing keys.

    Raises:
        SystemExit: If the config file is missing, has invalid YAML, or contains
            invalid values.
    """
    try:
        with open(config_path) as f:
            user_config = yaml.safe_load(f)
    except FileNotFoundError:
        raise SystemExit(f"Config file not found: {config_path}")
    except yaml.YAMLError as exc:
        raise SystemExit(f"Invalid YAML in config file {config_path}: {exc}")

    # safe_load returns None for empty files
    if user_config is None:
        user_config = {}

    config = _deep_merge(DEFAULTS, user_config)

    # Expand ~ in output_dir
    config["storage"]["output_dir"] = str(
        Path(config["storage"]["output_dir"]).expanduser()
    )

    _validate(config)

    return config
