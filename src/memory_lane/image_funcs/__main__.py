from memory_lane.image_funcs import Path, get_device_fingerprint


def main(argv=None):

    import argparse

    parser = argparse.ArgumentParser(description="Memory Lane: Organize your memories")
    parser.add_argument("image", type=Path, help="")

    args = parser.parse_args(argv)

    assert args.image.is_file()

    get_device_fingerprint(args.image)


if __name__ == "__main__":
    main()
