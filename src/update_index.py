import argparse

import pathlib
from util import die_error
from paths import get_cwd_relative
from staging import Index, parse_index

def setup_parser(parser):
    parser.add_argument("file",nargs="*",help="files to update")

def update_index(args):
    files = args.file
    cwd = get_cwd_relative()
    files = list(map(lambda f: str(cwd / f), files))
    index = parse_index()
    for f in files:
        exists = index.check_registerd(f)
        if not exists:
            die_error(f"error: {f} not registered to index. consider using --add option.")
    index.update(files)

def main():
    parser = argparse.ArgumentParser()
    setup_parser(parser)
    args = parser.parse_args()
    update_index(args)

if __name__ == "__main__":
    main()
