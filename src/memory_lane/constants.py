IMAGE_EXTENSIONS: list[str] = [".jpg", ".jpeg", ".png", ".heic"]
VIDEO_EXTENSIONS: list[str] = [".mov", ".mp4"]
SUPPORTED_EXTENSIONS: list[str] = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

COLUMN_FILENAME = "filename"
COLUMN_DATETIME = "datetime"
COLUMN_AUTHOR = "author"
COLUMN_HASH = "hash"

# Calculated columns
COLUMN_BEST_NAME = "best_name"

# ExifTags.Base
EXIF_DATETIME = "datetime"
EXIF_DEVICE = "Camera Model Name"
EXIF_DEVICE_FINGERPRINT = "Software"
EXIF_GPS_LAG = "GPS Latitude"
EXIF_GPS_LONG = "GPS Longitude"

# Formats
DATE_FORMAT = "%Y-%m-%d-%H%M-%S"
