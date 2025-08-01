# tests/conftest.py
import pytest
from pathlib import Path
from PIL import Image, ImageDraw, ExifTags
from datetime import datetime
import os

@pytest.fixture
def media_test_folder(tmp_path: Path) -> tuple[Path, list[str], list[str]]:
    """
    Creates a temporary folder with a mix of media and non-media files for testing.

    Returns a tuple containing:
    - The path to the temporary folder.
    - A list of filenames expected to be processed.
    - A list of filenames expected to be ignored.
    """
    def create_test_image(path: str, text: str, creation_time: datetime, artist: str | None = None):
        """Creates a test image with text, creation time, and an optional artist in the EXIF data."""
        img = Image.new('RGB', (400, 300), color='blue')
        d = ImageDraw.Draw(img)
        d.text((10, 10), text, fill=(255, 255, 0))

        exif = img.getexif()
        exif[ExifTags.Base.DateTime] = creation_time.strftime("%Y:%m:%d %H:%M:%S")
        if artist:
            exif[ExifTags.Base.Artist] = artist
        
        img.save(path, exif=exif)

    # --- Create Files ---
    processed_files = [
        "image_with_artist.jpg",
        "image_without_artist.png",
        "video1.mov",
        "image_duplicate.jpg",
    ]
    ignored_files = ["desktop.ini", "notes.txt", "archive.zip"]

    # Create an image with an artist tag
    create_test_image(
        os.path.join(tmp_path, "image_with_artist.jpg"),
        "Image With Artist",
        datetime(2023, 10, 1, 10, 0, 0),
        artist="TestArtist"
    )

    # Create an image without an artist tag
    create_test_image(
        os.path.join(tmp_path, "image_without_artist.png"),
        "Image Without Artist",
        datetime(2023, 10, 2, 11, 0, 0)
    )

    # Create a duplicate of the first image
    img1_data = open(os.path.join(tmp_path, "image_with_artist.jpg"), "rb").read()
    with open(os.path.join(tmp_path, "image_duplicate.jpg"), "wb") as f:
        f.write(img1_data)

    # Create dummy video and ignored files
    for filename in ["video1.mov"] + ignored_files:
        with open(os.path.join(tmp_path, filename), "w") as f:
            f.write(f"dummy content for {filename}")
            
    return tmp_path, processed_files, ignored_files