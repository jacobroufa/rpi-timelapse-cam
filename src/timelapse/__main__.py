"""CLI entry point for the timelapse capture daemon.

Usage:
    python -m timelapse [--config PATH]
"""

import argparse
import logging
import sys
from pathlib import Path

from timelapse.config import load_config
from timelapse.daemon import CaptureDaemon
from timelapse.storage import StorageManager


def main() -> None:
    """Parse arguments, load config, and start the capture daemon."""
    parser = argparse.ArgumentParser(
        prog="timelapse",
        description="Raspberry Pi timelapse capture daemon",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Path to YAML config file "
            "(default: /etc/timelapse/timelapse.yml or ./config/timelapse.yml)"
        ),
    )
    args = parser.parse_args()

    # Resolve config path with fallback chain
    if args.config is not None:
        config_path = args.config
    else:
        default_path = Path("/etc/timelapse/timelapse.yml")
        fallback_path = Path("./config/timelapse.yml")
        if default_path.exists():
            config_path = default_path
        elif fallback_path.exists():
            config_path = fallback_path
        else:
            print(
                "No config file found. Searched:\n"
                f"  1. {default_path}\n"
                f"  2. {fallback_path}\n"
                "Provide a config file with --config PATH or create one at "
                "either location.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Configure logging: INFO to stderr (systemd captures via journal)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    logger = logging.getLogger("timelapse")
    logger.info("Loading config from %s", config_path)

    config = load_config(config_path)

    # Validate output directory before starting daemon
    storage_cfg = config["storage"]
    storage = StorageManager(
        output_dir=Path(storage_cfg["output_dir"]),
        stop_threshold=storage_cfg["stop_threshold"],
        warn_threshold=storage_cfg["warn_threshold"],
    )
    storage.ensure_output_dir()

    # Create and run the daemon
    daemon = CaptureDaemon(config, config_path)
    daemon.run()


if __name__ == "__main__":
    main()
