from pathlib import Path

from memory_lane import enumerate_files
from memory_lane.constants import COLUMN_BEST_NAME, COLUMN_FILENAME


def test_renaming_logic(media_test_folder):
    test_folder, processed_files, ignored_files = media_test_folder
    df = enumerate_files(test_folder)
    # Simulate renaming
    for _, row in df.iterrows():
        old_name = row[COLUMN_FILENAME]
        new_name = row[COLUMN_BEST_NAME]
        assert new_name != old_name
        assert new_name.endswith(Path(old_name).suffix)
