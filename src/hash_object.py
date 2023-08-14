import argparse

from git_objects import Blob


def setup_parser(parser):
    parser.add_argument("file")
    parser.add_argument(
        "-w", help="write the object into the object database", action="store_true"
    )
    return parser


def hash_object(args):
    with open(args.file, "rb") as f:
        content = f.read()
    obj = Blob.from_content(content)
    sha1 = obj.hash()
    if args.w:
        obj.write()
    print(sha1)


def main():
    parser = argparse.ArgumentParser()
    setup_parser(parser)
    args = parser.parse_args()
    hash_object(args)


if __name__ == "__main__":
    main()
