import argparse

from staging import parse_index
from index_to_tree import index_to_file_tree

def setup_parser(parser):
    pass

def write_tree(args):
    index = parse_index()
    file_tree = index_to_file_tree(index)
    top = file_tree.write_tree_recursive()
    print(top.hash())

def main():
    parser = argparse.ArgumentParser()
    setup_parser(parser)
    args = parser.parse_args()
    write_tree(args)

if __name__ == "__main__":
    main()
