import argparse

import pathlib
from util import die_error
from paths import get_cwd_relative
from staging import Index, IndexEntry, parse_index

def setup_parser(parser):
    parser.add_argument("--add",help="add files to index",action="store_true")
    parser.add_argument("file",nargs="*",help="files to update")

def update_index(args):
    files = args.file
    cwd = get_cwd_relative()
    paths_relative_to_root = set(map(lambda f: str(cwd / f), files))
    index = parse_index()
    for p in paths_relative_to_root:
        exists = index.check_registerd(p)
        if not exists:
            if args.add:
                index.add_entry(IndexEntry.from_path(p))
            else:
                file = pathlib.Path(p).relative_to(get_cwd_relative())
                die_error(f"error: {file} not registered to index. consider using --add option.")
    index.update(paths_relative_to_root)

def main():
    parser = argparse.ArgumentParser()
    setup_parser(parser)
    args = parser.parse_args()
    update_index(args)

if __name__ == "__main__":
    main()
