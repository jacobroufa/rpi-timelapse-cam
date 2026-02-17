"""Thumbnail generation for timelapse images.

Generates 120px JPEG thumbnails in a thumbs/ subdirectory alongside
the original images. Thumbnails are pre-generated at capture time for
fast timeline browsing on the Pi.
"""

from pathlib import Path

from PIL import Image


def generate_thumbnail(
    image_path: Path, thumb_dir: Path | None = None
) -> Path:
    """Generate a 120px JPEG thumbnail for the given image.

    Args:
        image_path: Path to the source image file.
        thumb_dir: Directory to store the thumbnail. Defaults to
            ``image_path.parent / "thumbs"``.

    Returns:
        Path to the generated (or already existing) thumbnail file.
    """
    if thumb_dir is None:
        thumb_dir = image_path.parent / "thumbs"

    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_dir / image_path.name

    # Idempotent: skip if thumbnail already exists
    if thumb_path.exists():
        return thumb_path

    with Image.open(image_path) as im:
        im.thumbnail((120, 120))
        im.save(thumb_path, "JPEG", quality=60)

    return thumb_path
