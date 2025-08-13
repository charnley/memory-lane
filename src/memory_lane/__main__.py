import argparse
import sys
from pathlib import Path

from memory_lane import enumerate_files, file_funcs
from memory_lane.constants import COLUMN_BEST_NAME, COLUMN_FILENAME

# TODO Find best filename, and ensure there are no conflicts, if conflict add minified hash and try again


def move_file(dir, row):
    filename1 = dir / row[COLUMN_FILENAME]
    filename2 = dir / row[COLUMN_BEST_NAME]
    file_funcs.rename_file(filename1, filename2)


def main(argv=None):

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Memory Lane: Organize your memories")
    parser.add_argument("folder", type=Path, help="")

    args = parser.parse_args(argv)

    assert args.folder is not None
    assert args.folder.is_dir()

    images = enumerate_files(args.folder)
    # Check for duplicates

    print(images)

    images.to_csv("test.csv")

    images.apply(lambda row: move_file(args.folder, row), axis=1)


if __name__ == "__main__":
    main()
