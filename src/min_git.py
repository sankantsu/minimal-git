#!/usr/bin/env python3

from util import get_logger
import hash_object
import cat_file
import ls_files
import read_tree
import write_tree
import update_index
import commit_tree

logger = get_logger()


def setup_parser(parser):
    parser.add_argument(
        "--verbose", "-v", help="more verbose output", action="store_true"
    )
    parser.set_defaults(subcommand=lambda _: parser.print_help())


def set_verbose_logging(logger):
    import logging

    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    setup_parser(parser)

    subparsers = parser.add_subparsers()

    def add_subcommand(name, help, setup, func):
        subparser = subparsers.add_parser(name, help=help)
        setup(subparser)
        subparser.set_defaults(subcommand=func)

    add_subcommand(
        "hash-object",
        help="Compute object ID",
        setup=hash_object.setup_parser,
        func=hash_object.hash_object,
    )
    add_subcommand(
        "cat-file",
        help="Provide content or type and size information for repository objects",
        setup=cat_file.setup_parser,
        func=cat_file.cat_file,
    )
    add_subcommand(
        "ls-files",
        help="Show information about files in the index and the working tree",
        setup=ls_files.setup_parser,
        func=ls_files.ls_files,
    )
    add_subcommand(
        "read-tree",
        help="Reads tree information into the index",
        setup=read_tree.setup_parser,
        func=read_tree.read_tree,
    )
    add_subcommand(
        "write-tree",
        help="Create a tree object from the current index",
        setup=write_tree.setup_parser,
        func=write_tree.write_tree,
    )
    add_subcommand(
        "update-index",
        help="Register file contents in the working tree to the index",
        setup=update_index.setup_parser,
        func=update_index.update_index,
    )
    add_subcommand(
        "commit-tree",
        help="Create a new commit object",
        setup=commit_tree.setup_parser,
        func=commit_tree.commit_tree,
    )

    args = parser.parse_args()
    if args.verbose:
        set_verbose_logging(logger)

    args.subcommand(args)


if __name__ == "__main__":
    main()
