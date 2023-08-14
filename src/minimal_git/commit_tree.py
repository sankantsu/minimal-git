import argparse

from .paths import find_object
from .git_objects import Commit


def setup_parser(parser):
    parser.add_argument(
        "-p",
        dest="parents",
        metavar="<parent>",
        help="each -p indicate parent commit",
        action="append",
    )
    parser.add_argument("tree", metavar="<tree>", help="tree to commit")


def commit_tree(args):
    commit_message = input()
    tree = find_object(args.tree)
    parents = args.parents or []
    commit = Commit.from_tree(tree, parents, commit_message)
    commit.write()
    print(commit.hash())


def main():
    parser = argparse.ArgumentParser()
    setup_parser(parser)
    args = parser.parse_args()
    commit_tree(args)


if __name__ == "__main__":
    main()
