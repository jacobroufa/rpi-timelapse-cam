"""CLI entry point for the timelapse capture daemon and video generator.

Usage:
    python -m timelapse [--config PATH]              # run daemon (default)
    python -m timelapse generate-thumbnails [--config PATH]  # backfill thumbnails
    python -m timelapse generate --start DATE [--end DATE | --range RANGE]  # generate video
"""

import argparse
import logging
import sys
from datetime import date
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


def _run_generate(args: argparse.Namespace) -> None:
    """Run the timelapse video generation pipeline."""
    from timelapse.generate import generate_timelapse, range_to_end_date

    # Parse --resolution string "WxH" into tuple if provided
    resolution = None
    if args.resolution:
        try:
            w, h = args.resolution.lower().split("x")
            resolution = (int(w), int(h))
        except (ValueError, AttributeError):
            print(
                f"Invalid resolution: '{args.resolution}'. Use WxH format (e.g. 1920x1080).",
                file=sys.stderr,
            )
            sys.exit(1)

    # Determine images directory
    if args.images:
        images_dir = args.images
    else:
        config_path = _resolve_config(args.config)
        config = load_config(config_path)
        images_dir = Path(config["storage"]["output_dir"])

    # Compute end date
    if hasattr(args, "range") and args.range:
        end_date = range_to_end_date(args.start, args.range)
    else:
        end_date = args.end

    generate_timelapse(
        images_dir=images_dir,
        start=args.start,
        end=end_date,
        duration_seconds=args.duration,
        output_path=args.output,
        use_thumbnails=args.thumbnails,
        every_n=args.every,
        sort=args.sort,
        resolution=resolution,
        codec=args.codec,
        dry_run=args.dry_run,
        show_progress=not args.summary_only,
        verbose=args.verbose,
        silent=args.silent,
    )


def main() -> None:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        prog="timelapse",
        description="Raspberry Pi timelapse capture daemon and video generator",
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

    # generate subcommand
    from timelapse.generate import parse_duration, parse_range

    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate a timelapse video from captured images",
    )
    gen_parser.add_argument(
        "--start",
        required=True,
        type=lambda s: date.fromisoformat(s),
        help="Start date (YYYY-MM-DD)",
    )
    date_group = gen_parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        "--end",
        type=lambda s: date.fromisoformat(s),
        help="End date (YYYY-MM-DD)",
    )
    date_group.add_argument(
        "--range",
        type=parse_range,
        help="Date range relative to start (e.g. 7d, 2w, 1m)",
    )
    gen_parser.add_argument(
        "--duration",
        type=parse_duration,
        default=120,
        help="Target video duration (e.g. 2m, 90s, 1h30m). Default: 2m",
    )
    gen_parser.add_argument(
        "--images",
        type=Path,
        default=None,
        help="Image directory (overrides config output_dir)",
    )
    gen_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output video file path (default: ./timelapse_START_END.mp4)",
    )
    gen_parser.add_argument(
        "--thumbnails",
        action="store_true",
        help="Use thumbnail images for quick preview",
    )
    gen_parser.add_argument(
        "--every",
        type=int,
        default=1,
        help="Use every Nth image (default: 1 = all)",
    )
    gen_parser.add_argument(
        "--sort",
        choices=["filename", "mtime", "random"],
        default="filename",
        help="Image sort order (default: filename)",
    )
    gen_parser.add_argument(
        "--resolution",
        type=str,
        default=None,
        help="Output resolution WxH (e.g. 1920x1080). Default: source resolution",
    )
    gen_parser.add_argument(
        "--codec",
        type=str,
        default="libx264",
        help="FFmpeg video codec (default: libx264)",
    )
    gen_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without encoding",
    )
    gen_parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Suppress progress bar, show only final summary",
    )
    gen_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output including FFmpeg messages",
    )
    gen_parser.add_argument(
        "--silent",
        action="store_true",
        help="Suppress gap warnings",
    )
    gen_parser.add_argument(
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
    elif args.command == "generate":
        _run_generate(args)
    else:
        # Default: run the daemon
        _run_daemon(args)


if __name__ == "__main__":
    main()
