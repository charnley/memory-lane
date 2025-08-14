from memory_lane import enumerate_files
from memory_lane.constants import (
    COLUMN_AUTHOR,
    COLUMN_BEST_NAME,
    COLUMN_DATETIME,
    COLUMN_FILENAME,
    COLUMN_HASH,
)


def test_enumerate_files_basic(media_test_folder):
    test_folder, processed_files, ignored_files = media_test_folder
    df = enumerate_files(test_folder)
    # Check that all processed files are present
    for fname in processed_files:
        assert fname in df[COLUMN_FILENAME].values
    # Check columns
    for col in [COLUMN_FILENAME, COLUMN_HASH, COLUMN_DATETIME, COLUMN_AUTHOR, COLUMN_BEST_NAME]:
        assert col in df.columns
    # Check ignored files are not present
    for fname in ignored_files:
        assert fname not in df[COLUMN_FILENAME].values
