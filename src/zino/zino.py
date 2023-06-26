#!/usr/bin/env python3
import argparse
import asyncio
import logging
from datetime import datetime

from zino import state
from zino.scheduler import get_scheduler, load_and_schedule_polldevs

_log = logging.getLogger("zino")


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO if not args.debug else logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s (%(threadName)s) - %(message)s",
    )
    state.state = state.ZinoState.load_state_from_file() or state.ZinoState()
    init_event_loop(args)


def init_event_loop(args: argparse.Namespace):
    scheduler = get_scheduler()
    scheduler.start()

    scheduler.add_job(
        func=load_and_schedule_polldevs,
        trigger="interval",
        args=(args.polldevs.name,),
        minutes=1,
        next_run_time=datetime.now(),
    )
    scheduler.add_job(func=state.state.dump_state_to_file, trigger="interval", seconds=30)
    scheduler.add_job(func=state.state.dump_state_to_log, trigger="interval", seconds=30)

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

    return True


def parse_args(arguments=None):
    parser = argparse.ArgumentParser(description="Zino is not OpenView")
    parser.add_argument(
        "--polldevs", type=argparse.FileType("r"), metavar="PATH", default="polldevs.cf", help="Path to polldevs.cf"
    )
    parser.add_argument(
        "--debug", action="store_true", default=False, help="Set global log level to DEBUG. Very chatty!"
    )
    args = parser.parse_args(args=arguments)
    if args.polldevs:
        args.polldevs.close()  # don't leave this temporary file descriptor open
    return args


if __name__ == "__main__":
    main()
