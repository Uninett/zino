#!/usr/bin/env python3
import argparse
import asyncio
import logging
import operator
import sys
import time
from datetime import datetime, timedelta
from random import random

from zino.config.models import PollDevice
from zino.config.polldevs import read_polldevs
from zino.scheduler import init_scheduler

DEFAULT_INTERVAL_MINUTES = 5

_log = logging.getLogger("zino")


def main():
    parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s")

    if not init_async():
        sys.exit(1)


def init_async(polldevs_conf="polldevs.cf"):
    devices = sorted(read_polldevs(polldevs_conf), key=operator.attrgetter("priority"), reverse=True)
    _log.debug("Loaded %s devices from polldevs.cf", len(devices))
    if not devices:
        _log.error("No devices configured for polling")
        return False

    scheduler = init_scheduler()
    scheduler.start()

    # Spread poll jobs evenly across the entire default interval
    stagger_factor = (DEFAULT_INTERVAL_MINUTES * 60) / len(devices)
    for index, device in enumerate(devices):
        # Staggered job startup
        next_run_time = datetime.now() + timedelta(seconds=index * stagger_factor)

        scheduler.add_job(
            faux_poll,
            "interval",
            minutes=DEFAULT_INTERVAL_MINUTES,
            args=(device,),
            next_run_time=next_run_time,
            name=f"faux_poll({device.name!r})",
        )

    scheduler.add_job(blocking_operation, "interval", seconds=5)

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

    return True


def parse_args():
    parser = argparse.ArgumentParser(description="Zino is not OpenView")
    return parser.parse_args()


async def faux_poll(device: PollDevice):
    _log.debug("Fake polling %s in thread %s", device.name)
    await asyncio.sleep(random() * 5.0)


def blocking_operation():
    _log.info("blocking function called")
    time.sleep(1)


if __name__ == "__main__":
    main()
