import argparse

from git_objects import load_object

def setup_parser(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-p", help="pretty-print <object> content", action="store_true")
    group.add_argument("-t", help="show object type", action="store_true")
    parser.add_argument("object", help="sha1 digest of object")

def cat_file(args):
    obj = load_object(args.object)
    if args.t:
        print(obj.type_id)
    if args.p:
        print(obj)

def main():
    parser = argparse.ArgumentParser()
    setup_parser(parser)
    args = parser.parse_args()
    cat_file(args)

if __name__ == "__main__":
    main()
