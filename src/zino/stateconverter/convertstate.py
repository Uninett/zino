import argparse
import logging

from zino.state import ZinoState


def create_state(old_state_file: str) -> ZinoState:
    pass


def get_parser():
    parser = argparse.ArgumentParser(description="Convert Zino1 state to Zino2 compatible state")
    parser.add_argument(
        "input",
        help="Absolute path to the Zino1 state you want to convert",
    )
    parser.add_argument(
        "output",
        help="Absolute path to where the new Zino2 state should be dumped",
    )
    return parser


def main():
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    parser = get_parser()
    args = parser.parse_args()
    state = create_state(args.input)
    state.dump_state_to_file(args.output)


if __name__ == "__main__":
    main()
