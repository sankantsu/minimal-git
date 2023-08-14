import argparse

from .util import die_error
from .git_objects import load_object
from .staging import Index


def setup_parser(parser):
    parser.add_argument("tree")


def read_tree(args):
    tree = load_object(args.tree)
    if tree.type_id != "tree":
        die_error(f"error: {args.tree} is not a tree object")
    index = Index.from_tree(tree)
    index.write()


def main():
    parser = argparse.ArgumentParser()
    setup_parser(parser)
    args = parser.parse_args()
    read_tree(args)


if __name__ == "__main__":
    main()
