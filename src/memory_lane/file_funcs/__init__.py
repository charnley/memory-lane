import datetime
import logging
import os
from hashlib import md5
from pathlib import Path
from typing import Dict, List, Optional

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from hachoir.stream import InputIOStream
from PIL import ExifTags, Image

from memory_lane import image_funcs, video_funcs
from memory_lane.constants import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


def get_datetime(file_path: Path) -> Optional[datetime.datetime]:
    """
    Get the creation date of a file from its metadata.
    Falls back to the file's modification time if metadata is not available.

    Args:
        file_path (Path): Path to the file.

    Returns:
        datetime: Creation date of the file.
    """

    if file_path.suffix.lower() in IMAGE_EXTENSIONS:
        time = image_funcs.get_capture_datetime(file_path)
        return time

    elif file_path.suffix.lower() in VIDEO_EXTENSIONS:
        time = video_funcs.get_capture_datetime(file_path)
        return time

    # Fallback to file modification time
    stat = os.stat(file_path)
    return datetime.datetime.fromtimestamp(stat.st_mtime)


def rename_file(path1: Path, path2: Path):
    path1.rename(path2)
    return
