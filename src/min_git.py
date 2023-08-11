#!/usr/bin/env python3

import hash_object
import cat_file
import ls_files
import read_tree
import write_tree

def main():
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    parser.set_defaults(subcommand=lambda _: parser.print_help())

    def add_subcommand(name,help,setup,func):
        subparser = subparsers.add_parser(name,help=help)
        setup(subparser)
        subparser.set_defaults(subcommand=func)

    add_subcommand("hash-object",help="Compute object ID",
                   setup=hash_object.setup_parser,func=hash_object.hash_object)
    add_subcommand("cat-file",help="Provide content or type and size information for repository objects",
                   setup=cat_file.setup_parser,func=cat_file.cat_file)
    add_subcommand("ls-files",help="Show information about files in the index and the working tree",
                   setup=ls_files.setup_parser,func=ls_files.ls_files)
    add_subcommand("read-tree",help="Reads tree information into the index",
                   setup=read_tree.setup_parser,func=read_tree.read_tree)
    add_subcommand("write-tree",help="Create a tree object from the current index",
                   setup=write_tree.setup_parser,func=write_tree.write_tree)

    args = parser.parse_args()

    args.subcommand(args)

if __name__ == "__main__":
    main()
