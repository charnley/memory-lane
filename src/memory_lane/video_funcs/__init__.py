
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.stream import InputIOStream

DATE_PROPERTY = "creation_date"

def get_capture_datetime(file_path: Path) -> None | DateTime:

    with open(file_path, 'rb') as f:
        stream = InputIOStream(f)
        parser = createParser(stream)
        metadata = extractMetadata(parser)

        if not metadata:
            return None

        if not metadata.has(DATE_PROPERTY):
            return None

        time = metadata.get(DATE_PROPERTY)

        if time is None:
            return None

        # Get real datetime obj

    return datetime.
