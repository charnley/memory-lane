"""
image_manager.py

Core image and video management functions for Memory Lane CLI.
Handles duplicate detection, metadata extraction, and file renaming.
"""
import os
import logging
from hashlib import md5
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image, ExifTags
from datetime import datetime
import pillow_heif
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.stream import InputIOStream

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Register HEIF/HEIC support for Pillow
pillow_heif.register_heif_opener()

# Supported file extensions
IMAGE_EXTENSIONS: List[str] = ['.jpg', '.jpeg', '.png', '.heic']
VIDEO_EXTENSIONS: List[str] = ['.mov', '.mp4']
SUPPORTED_EXTENSIONS: List[str] = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

def _hash_file_in_chunks(file_path: Path) -> str:
    """
    Compute the MD5 hash of a file by reading it in chunks.

    Args:
        file_path (Path): Path to the file.

    Returns:
        str: Hexadecimal MD5 hash of the file, or empty string on error.
    """
    hasher = md5()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):  # Read in 8KB chunks
                hasher.update(chunk)
        return hasher.hexdigest()
    except IOError as e:
        logging.error(f"Could not read file {file_path} for hashing: {e}")
        return ""

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

def get_creation_date(file_path: Path) -> datetime:
    """
    Get the creation date of a file from its metadata.
    Falls back to the file's modification time if metadata is not available.

    Args:
        file_path (Path): Path to the file.

    Returns:
        datetime: Creation date of the file.
    """
    if file_path.suffix.lower() in IMAGE_EXTENSIONS:
        try:
            with Image.open(file_path) as img:
                exif = img.getexif()
                if exif:
                    creation_time_str = exif.get(ExifTags.Base.DateTime)
                    if creation_time_str:
                        return datetime.strptime(creation_time_str, "%Y:%m:%d %H:%M:%S")
        except Exception as e:
            logging.warning(f"Could not read EXIF data from {file_path.name}: {e}. Falling back to file modification time.")
    elif file_path.suffix.lower() in VIDEO_EXTENSIONS:
        try:
            with open(file_path, 'rb') as f:
                stream = InputIOStream(f)
                parser = createParser(stream)
                metadata = extractMetadata(parser)
                if metadata and metadata.has("creation_date"):
                    return metadata.get("creation_date")
        except Exception as e:
            logging.warning(f"Could not read metadata from {file_path.name}: {e}. Falling back to file modification time.")
    # Fallback to file modification time
    stat = os.stat(file_path)
    return datetime.fromtimestamp(stat.st_mtime)

def rename_image(image_path: Path, author_override: Optional[str] = None) -> Path:
    """
    Rename a media file based on its creation date and author.
    If author_override is provided, it is used. Otherwise, it checks for an 'Artist' tag in EXIF.

    Args:
        image_path (Path): Path to the image or video file.
        author_override (Optional[str]): Author name to use in filename. If None, tries to extract from metadata.

    Returns:
        Path: New file path after renaming (or original if unchanged).
    """
    try:
        creation_time = get_creation_date(image_path)
        author = author_override
        # Try to extract author from EXIF if not provided
        if not author and image_path.suffix.lower() in IMAGE_EXTENSIONS:
            try:
                with Image.open(image_path) as img:
                    exif = img.getexif()
                    if exif:
                        author = exif.get(ExifTags.Base.Artist)
            except Exception:
                logging.warning(f"Could not check for artist in {image_path.name}.")
        # Sanitize author name for filename
        author_str = f"-{author.replace(' ', '_')}" if author else ""
        new_name = f"{creation_time.strftime('%Y-%m-%d-%H%M%S')}{author_str}{image_path.suffix}"
        new_path = image_path.with_name(new_name)
        if new_path == image_path:
            return image_path  # Avoid renaming to the same name
        image_path.rename(new_path)
        return new_path
    except Exception as e:
        logging.error(f"Failed to rename {image_path.name}: {e}")
        return image_path
