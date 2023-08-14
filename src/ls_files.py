import argparse

import staging


def setup_parser(parser):
    parser.add_argument("--debug", help="show debugging data", action="store_true")


def ls_files(args):
    index = staging.parse_index()
    index.print(debug=args.debug)


def main():
    parser = argparse.ArgumentParser()
    setup_parser(parser)
    args = parser.parse_args()
    ls_files(args)


if __name__ == "__main__":
    main()
