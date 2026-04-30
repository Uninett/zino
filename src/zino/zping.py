"""Query a Zino daemon's SNMP agent to check if it is alive and report its uptime.

This module provides both a reusable async function for querying Zino's uptime via SNMP,
and a CLI entry point for quick health checks.
"""

import argparse
import asyncio
import sys

from pysnmp.hlapi.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    getCmd,
)

# ZINO-MIB::zinoUpTime.0
ZINO_UPTIME_OID = "1.3.6.1.4.1.2428.130.1.1.1.0"

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 60 * SECONDS_PER_MINUTE
SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR

_UPTIME_UNITS = (
    (SECONDS_PER_DAY, "day", "days"),
    (SECONDS_PER_HOUR, "hour", "hours"),
    (SECONDS_PER_MINUTE, "minute", "minutes"),
    (1, "second", "seconds"),
)


def main():
    """CLI entry point for zping."""
    parser = argparse.ArgumentParser(description="Check if a Zino daemon is alive by querying its SNMP agent")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="Host to query (default: 127.0.0.1)")
    parser.add_argument("port", nargs="?", type=int, default=8000, help="UDP port (default: 8000)")
    parser.add_argument("--community", default="public", help="SNMP community (default: public)")
    parser.add_argument("--timeout", type=int, default=5, help="Timeout in seconds (default: 5)")
    args = parser.parse_args()

    try:
        uptime = asyncio.run(
            get_zino_uptime(host=args.host, port=args.port, community=args.community, timeout=args.timeout)
        )
    except ZpingError as error:
        print(f"Zino is not reachable at {args.host}:{args.port} ({error})", file=sys.stderr)
        raise SystemExit(1)

    print(f"Zino is alive (uptime: {format_uptime(uptime)})")


async def get_zino_uptime(
    host: str = "127.0.0.1", port: int = 8000, community: str = "public", timeout: int = 5
) -> int:
    """Query a Zino SNMP agent for its uptime.

    :param host: Hostname or IP address of the Zino agent
    :param port: UDP port the Zino SNMP agent listens on
    :param community: SNMP community string
    :param timeout: Timeout in seconds for the SNMP request
    :return: Uptime in seconds
    :raises ZpingError: When the agent is unreachable or returns an error
    """
    snmp_engine = SnmpEngine()

    try:
        error_indication, error_status, error_index, var_binds = await getCmd(
            snmp_engine,
            CommunityData(community),
            UdpTransportTarget((host, port), timeout=timeout, retries=0),
            ContextData(),
            ObjectType(ObjectIdentity(ZINO_UPTIME_OID)),
        )
    except Exception as exc:
        snmp_engine.closeDispatcher()
        raise ZpingError(f"SNMP request failed: {exc}") from exc

    snmp_engine.closeDispatcher()

    if error_indication:
        raise ZpingError(str(error_indication))
    if error_status:
        raise ZpingError(
            f"SNMP error: {error_status.prettyPrint()} at {var_binds[int(error_index) - 1][0] if error_index else '?'}"
        )
    if not var_binds:
        raise ZpingError("Empty response from agent")

    _, value = var_binds[0]
    return int(value)


def format_uptime(seconds: int) -> str:
    """Format an uptime value in seconds to a human-readable string.

    Zero-valued components are omitted. For example, 90061 seconds becomes
    ``"1 day, 1 hour, 1 second"`` (skipping minutes since they are zero).

    :param seconds: Uptime in seconds (non-negative)
    :return: Human-readable uptime string
    """
    if seconds < 0:
        raise ValueError("Uptime cannot be negative")
    if seconds == 0:
        return "0 seconds"

    parts = []
    remainder = seconds
    for unit_seconds, singular, plural in _UPTIME_UNITS:
        count, remainder = divmod(remainder, unit_seconds)
        if count:
            parts.append(f"{count} {singular if count == 1 else plural}")

    return ", ".join(parts)


class ZpingError(Exception):
    """Raised when a Zino uptime query fails."""


if __name__ == "__main__":
    main()
