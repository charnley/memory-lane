import argparse
import sys
from pathlib import Path

# from .image_manager import find_duplicate_images, rename_image, SUPPORTED_EXTENSIONS


def main(argv=None):

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Memory Lane CLI: Organize, deduplicate, and rename your photo and video collections."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # find-duplicates command
    parser_find_duplicates = subparsers.add_parser(
        "find-duplicates", help="Find duplicate media files in a folder based on file content."
    )
    parser_find_duplicates.add_argument(
        "folder", type=Path, help="Path to the folder to search for duplicate files."
    )

    # rename command
    parser_rename = subparsers.add_parser(
        "rename", help="Rename media files in a folder based on their creation date and author."
    )
    parser_rename.add_argument(
        "folder", type=Path, help="Path to the folder containing files to rename."
    )
    parser_rename.add_argument(
        "--author",
        type=str,
        help="Override author name for all files. If not provided, uses metadata if available.",
    )

    args = parser.parse_args(argv)

    if args.command == "find-duplicates":
        if not args.folder.exists() or not args.folder.is_dir():
            print(f"Error: Folder '{args.folder}' does not exist or is not a directory.")
            sys.exit(1)
        duplicates = find_duplicate_images(args.folder)
        if duplicates:
            print("Found duplicate files:")
            for file_hash, paths in duplicates.items():
                print(f"  Hash: {file_hash}")
                for path in sorted(paths):  # Sort for consistent output
                    print(f"    - {path.name}")
        else:
            print("No duplicate files found.")

    elif args.command == "rename":
        if not args.folder.exists() or not args.folder.is_dir():
            print(f"Error: Folder '{args.folder}' does not exist or is not a directory.")
            sys.exit(1)
        print(f"Renaming files in '{args.folder}'...")
        renamed_count = 0
        for file_path in sorted(args.folder.iterdir()):  # Sort for consistent processing
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                new_path = rename_image(file_path, author_override=args.author)
                if new_path != file_path:
                    print(f"Renamed {file_path.name} to {new_path.name}")
                    renamed_count += 1
        print(f"Finished. Renamed {renamed_count} file(s).")


if __name__ == "__main__":
    main()
