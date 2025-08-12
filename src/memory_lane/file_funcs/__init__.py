import logging
import os
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Dict, List, Optional

import pillow_heif
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from hachoir.stream import InputIOStream
from PIL import ExifTags, Image

from memory_lane import image_funcs
from memory_lane.constants import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

# Register HEIF/HEIC support for Pillow
pillow_heif.register_heif_opener()


def _hash_file_in_chunks(file_path: Path) -> str:
    """
    Compute the MD5 hash of a file by reading it in chunks.

    Args:
        file_path (Path): Path to the file.

    Returns:
        str: Hexadecimal MD5 hash of the file, or empty string on error.
    """
    hasher = md5()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):  # Read in 8KB chunks
                hasher.update(chunk)
        return hasher.hexdigest()
    except IOError as e:
        logging.error(f"Could not read file {file_path} for hashing: {e}")
        return ""


def get_creation_date(file_path: Path) -> datetime:
    """
    Get the creation date of a file from its metadata.
    Falls back to the file's modification time if metadata is not available.

    Args:
        file_path (Path): Path to the file.

    Returns:
        datetime: Creation date of the file.
    """

    # TODO Move away from this funcs, should be in main init
    if file_path.suffix.lower() in IMAGE_EXTENSIONS:
        time = image_funcs.get_capture_datetime(file_path)
        return time

    elif file_path.suffix.lower() in VIDEO_EXTENSIONS:
        time = video_funcs.get_capture_datetime(file_path)
        return time

    # Fallback to file modification time
    stat = os.stat(file_path)
    return datetime.fromtimestamp(stat.st_mtime)


def rename_file(path: Path, author_override: Optional[str] = None) -> Path:
    """
    Rename a media file based on its creation date and author.
    If author_override is provided, it is used. Otherwise, it checks for an 'Artist' tag in EXIF.

    Args:
        image_path (Path): Path to the image or video file.
        author_override (Optional[str]): Author name to use in filename. If None, tries to extract from metadata.

    Returns:
        Path: New file path after renaming (or original if unchanged).
    """
    try:
        creation_time = get_creation_date(image_path)
        author = author_override
        # Try to extract author from EXIF if not provided
        if not author and image_path.suffix.lower() in IMAGE_EXTENSIONS:
            try:
                with Image.open(image_path) as img:
                    exif = img.getexif()
                    if exif:
                        author = exif.get(ExifTags.Base.Artist)
            except Exception:
                logging.warning(f"Could not check for artist in {image_path.name}.")
        # Sanitize author name for filename
        author_str = f"-{author.replace(' ', '_')}" if author else ""
        new_name = f"{creation_time.strftime('%Y-%m-%d-%H%M%S')}{author_str}{image_path.suffix}"
        new_path = image_path.with_name(new_name)
        if new_path == image_path:
            return image_path  # Avoid renaming to the same name
        image_path.rename(new_path)
        return new_path
    except Exception as e:
        logging.error(f"Failed to rename {image_path.name}: {e}")
        return image_path
