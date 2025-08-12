def find_duplicate_images(folder_path: Path) -> Dict[str, List[Path]]:
    """
    Find duplicate media files in a folder based on their content hash.

    Args:
        folder_path (Path): Path to the folder to scan.

    Returns:
        Dict[str, List[Path]]: Mapping of hash to list of duplicate file paths.
    """
    hashes: Dict[str, List[Path]] = {}
    for file_path in folder_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            file_hash = _hash_file_in_chunks(file_path)
            if not file_hash:
                continue
            if file_hash not in hashes:
                hashes[file_hash] = []
            hashes[file_hash].append(file_path)
    # Only return hashes with more than one file (duplicates)
    return {key: value for key, value in hashes.items() if len(value) > 1}
