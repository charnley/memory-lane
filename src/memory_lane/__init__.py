import hashlib
from pathlib import Path

import pandas as pd

from memory_lane.constants import (
    COLUMN_AUTHOR,
    COLUMN_BEST_NAME,
    COLUMN_DATETIME,
    COLUMN_FILENAME,
    COLUMN_HASH,
    DATE_FORMAT,
    SUPPORTED_EXTENSIONS,
)
from memory_lane.file_funcs import get_datetime
from memory_lane.image_funcs import get_device_fingerprint

BUF_SIZE = 65536


def enumerate_files(dir) -> pd.DataFrame:

    file_names = []

    for x in dir.iterdir():

        if not x.is_file():
            continue

        if x.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        file_names.append(x.name)

    pdf = pd.DataFrame({COLUMN_FILENAME: file_names})
    pdf[COLUMN_HASH] = pdf[COLUMN_FILENAME].map(lambda f: get_filename_hash(dir / f))
    pdf[COLUMN_DATETIME] = pdf[COLUMN_FILENAME].map(lambda f: get_datetime(dir / f))
    pdf[COLUMN_AUTHOR] = pdf[COLUMN_FILENAME].map(lambda f: get_device_fingerprint(dir / f))
    pdf[COLUMN_BEST_NAME] = pdf.apply(get_best_name, axis=1)

    return pdf


def get_filename_hash(filename):
    sha1 = hashlib.sha1()
    with open(filename, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def cut_duplicates(pdf):

    duplicates = pd.DataFrame()

    return duplicates, pdf


def get_best_name(row):

    if isinstance(row[COLUMN_DATETIME], pd.Timestamp):
        str_date = row[COLUMN_DATETIME].strftime(DATE_FORMAT)

    else:
        str_date = "unknown_date"

    filename1 = Path(row[COLUMN_FILENAME])
    suffix = filename1.suffix

    hash = row[COLUMN_HASH]

    new_filename = f"{str_date}-{hash:.5s}{suffix}"

    return new_filename
