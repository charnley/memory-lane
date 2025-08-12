from datetime import DateTime
from pathlib import Path

from PIL import ExifTags, Image


def get_capture_timedate(file_path: Path) -> None | DateTime:

    with Image.open(file_path) as img:
        exif = img.getexif()

        if not exif:
            return None

        creation_time_str = exif.get(ExifTags.Base.DateTime)

        if not creation_time_str:
            return None

        return datetime.strptime(creation_time_str, "%Y:%m:%d %H:%M:%S")
