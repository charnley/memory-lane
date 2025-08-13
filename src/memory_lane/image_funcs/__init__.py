import hashlib
from datetime import datetime
from pathlib import Path

import pillow_heif
from PIL import ExifTags, Image

from memory_lane.constants import EXIF_DEVICE, EXIF_DEVICE_FINGERPRINT, IMAGE_EXTENSIONS

# Register HEIF/HEIC support for Pillow
pillow_heif.register_heif_opener()


def get_image_metadata():

    return


def get_capture_datetime(file_path: Path):

    with Image.open(file_path) as img:
        exif = img.getexif()

        if not exif:
            return None

        creation_time_str = exif.get(ExifTags.Base.DateTime)

    if not creation_time_str:
        return None

    return datetime.strptime(creation_time_str, "%Y:%m:%d %H:%M:%S")


def get_device_fingerprint(file_path):

    if file_path.suffix not in IMAGE_EXTENSIONS:
        return None

    with Image.open(file_path) as img:
        exif = img.getexif()

        if not exif:
            return None

        device_model = exif.get(ExifTags.Base.Model)
        device_make = exif.get(ExifTags.Base.Make)
        device_software = exif.get(ExifTags.Base.Software)

    # fp = {
    #     EXIF_DEVICE: device_model,
    #     EXIF_MAKE: device_make,
    #     EXIF_SOFTWARE: device_software,
    # }

    if device_model is not None:

        sha1 = hashlib.sha1()
        sha1.update(device_model.encode())
        return sha1.hexdigest()

    return None
