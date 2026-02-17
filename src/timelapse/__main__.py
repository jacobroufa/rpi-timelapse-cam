"""CLI entry point for the timelapse capture daemon.

Usage:
    python -m timelapse [--config PATH]              # run daemon (default)
    python -m timelapse generate-thumbnails [--config PATH]  # backfill thumbnails
"""

import argparse
import logging
import sys
from pathlib import Path

from timelapse.config import load_config
from timelapse.daemon import CaptureDaemon
from timelapse.storage import StorageManager


def _resolve_config(config_arg: Path | None) -> Path:
    """Resolve the config file path using the standard fallback chain.

    Args:
        config_arg: Explicit --config value, or None for fallback chain.

    Returns:
        Resolved path to an existing config file.

    Raises:
        SystemExit: If no config file is found.
    """
    if config_arg is not None:
        return config_arg

    default_path = Path("/etc/timelapse/timelapse.yml")
    fallback_path = Path("./config/timelapse.yml")

    if default_path.exists():
        return default_path
    if fallback_path.exists():
        return fallback_path

    print(
        "No config file found. Searched:\n"
        f"  1. {default_path}\n"
        f"  2. {fallback_path}\n"
        "Provide a config file with --config PATH or create one at "
        "either location.",
        file=sys.stderr,
    )
    sys.exit(1)


def _run_daemon(args: argparse.Namespace) -> None:
    """Run the capture daemon (default subcommand)."""
    config_path = _resolve_config(args.config)

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


def _run_generate_thumbnails(args: argparse.Namespace) -> None:
    """Walk output directory and generate thumbnails for existing images."""
    from timelapse.web.thumbnails import generate_thumbnail

    config_path = _resolve_config(args.config)

    logger = logging.getLogger("timelapse")
    logger.info("Loading config from %s", config_path)

    config = load_config(config_path)
    output_dir = Path(config["storage"]["output_dir"])

    if not output_dir.exists():
        print(f"Output directory does not exist: {output_dir}", file=sys.stderr)
        sys.exit(1)

    generated = 0
    skipped = 0
    total = 0

    # Walk the output directory tree looking for .jpg files
    for image_path in sorted(output_dir.rglob("*.jpg")):
        # Skip files already inside a thumbs/ directory
        if "thumbs" in image_path.parts:
            continue

        total += 1
        thumb_dir = image_path.parent / "thumbs"
        thumb_path = thumb_dir / image_path.name

        if thumb_path.exists():
            skipped += 1
            continue

        try:
            generate_thumbnail(image_path)
            # Derive a relative display path: YYYY/MM/DD/HHMMSS.jpg
            rel = image_path.relative_to(output_dir)
            print(f"Generated thumbnail for {rel}")
            generated += 1
        except Exception as exc:
            logger.warning("Failed to generate thumbnail for %s: %s", image_path, exc)

    print(
        f"Generated {generated} thumbnails for {total} images "
        f"({skipped} already had thumbnails)"
    )


def main() -> None:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        prog="timelapse",
        description="Raspberry Pi timelapse capture daemon",
    )

    # Global --config option
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Path to YAML config file "
            "(default: /etc/timelapse/timelapse.yml or ./config/timelapse.yml)"
        ),
    )

    subparsers = parser.add_subparsers(dest="command")

    # generate-thumbnails subcommand
    thumb_parser = subparsers.add_parser(
        "generate-thumbnails",
        help="Generate thumbnails for existing images (backfill)",
    )
    thumb_parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Path to YAML config file "
            "(default: /etc/timelapse/timelapse.yml or ./config/timelapse.yml)"
        ),
    )

    # Configure logging: INFO to stderr (systemd captures via journal)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    args = parser.parse_args()

    if args.command == "generate-thumbnails":
        _run_generate_thumbnails(args)
    else:
        # Default: run the daemon
        _run_daemon(args)


if __name__ == "__main__":
    main()
