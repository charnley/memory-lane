from memory_lane import cut_duplicates, enumerate_files


def test_cut_duplicates(media_test_folder):
    test_folder, processed_files, ignored_files = media_test_folder
    df = enumerate_files(test_folder)
    duplicates, unique = cut_duplicates(df)
    # There should be at least one duplicate (image_duplicate.jpg)
    assert not duplicates.empty
    # All unique files should be in processed_files
    for fname in unique["filename"]:
        assert fname in processed_files
