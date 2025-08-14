from memory_lane import enumerate_files


def test_ignored_files(media_test_folder):
    test_folder, processed_files, ignored_files = media_test_folder
    df = enumerate_files(test_folder)
    # Ignored files should not be present
    for fname in ignored_files:
        assert fname not in df["filename"].values
