"""Age-based cleanup of day directories."""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("timelapse.storage.cleanup")


def cleanup_old_days(output_dir: Path, retention_days: int) -> int:
    """Delete day directories older than the retention period.

    Walks the YYYY/MM/DD directory structure under output_dir. For each day
    directory whose date is older than ``datetime.now() - timedelta(days=retention_days)``,
    removes the entire day directory with ``shutil.rmtree()``.

    Non-date directories are silently skipped. After removing day directories,
    empty month and year directories are cleaned up.

    Args:
        output_dir: Base directory containing the YYYY/MM/DD structure.
        retention_days: Number of days to retain. Days older than this are deleted.

    Returns:
        Count of day directories deleted.
    """
    output_dir = Path(output_dir)
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = 0

    if not output_dir.is_dir():
        return 0

    # Walk year/month/day structure, sorted so oldest are processed first
    for year_dir in sorted(output_dir.iterdir()):
        if not year_dir.is_dir():
            continue

        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue

            for day_dir in sorted(month_dir.iterdir()):
                if not day_dir.is_dir():
                    continue

                try:
                    dir_date = datetime.strptime(
                        f"{year_dir.name}/{month_dir.name}/{day_dir.name}",
                        "%Y/%m/%d",
                    )
                except ValueError:
                    # Not a valid date directory -- skip silently
                    continue

                if dir_date < cutoff:
                    shutil.rmtree(day_dir)
                    deleted += 1
                    logger.info("Deleted old day directory: %s", day_dir)

            # Clean up empty month directory
            if month_dir.is_dir() and not any(month_dir.iterdir()):
                month_dir.rmdir()
                logger.debug("Removed empty month directory: %s", month_dir)

        # Clean up empty year directory
        if year_dir.is_dir() and not any(year_dir.iterdir()):
            year_dir.rmdir()
            logger.debug("Removed empty year directory: %s", year_dir)

    return deleted
