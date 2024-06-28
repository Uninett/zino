#!/usr/bin/env python3
"""Fetch SNMP agent uptime using Zino high-level APIs"""
import argparse
import asyncio
import logging

from zino.config.polldevs import read_polldevs
from zino.snmp import SNMP
from zino.state import config

_log = logging.getLogger(__name__)


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s (%(threadName)s) - %(message)s"
    )
    asyncio.get_event_loop().run_until_complete(run(args))


async def run(args: argparse.Namespace):
    devices = {d.name: d for d in read_polldevs(config.polling.file)}
    device = devices[args.router]

    snmp = SNMP(device)
    response = await snmp.get("SNMPv2-MIB", "sysUpTime", 0)
    _log.info("Response from %s: %r", device.name, int(response))


def parse_args():
    devicenames = [d.name for d in read_polldevs(config.polling.file)]
    parser = argparse.ArgumentParser(description="Fetch sysUptime from a device in the pollfile")
    parser.add_argument("router", type=str, help="Zino router name", choices=devicenames)
    return parser.parse_args()


if __name__ == "__main__":
    main()
