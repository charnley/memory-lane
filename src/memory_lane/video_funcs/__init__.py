from pathlib import Path

from hachoir.metadata import extractMetadata  # type: ignore
from hachoir.parser import createParser  # type: ignore

DATE_PROPERTY = "creation_date"

# TODO Not possible to get device information?


def get_capture_datetime(file_path: Path):

    parser = createParser(str(file_path))
    metadata = extractMetadata(parser)

    if not metadata:
        return None

    if not metadata.has(DATE_PROPERTY):
        return None

    time = metadata.get(DATE_PROPERTY)

    if time is None:
        return None

    return time
