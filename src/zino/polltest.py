#!/usr/bin/env python3
"""Test SNMP polling using the PySNMP high-level API directly"""

import argparse
import asyncio
import logging

from pysnmp.hlapi.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    bulkCmd,
    isEndOfMib,
)

_log = logging.getLogger("polltest")


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s (%(threadName)s) - %(message)s"
    )
    asyncio.run(run(args))


async def run(args: argparse.Namespace):
    snmp_engine = SnmpEngine()
    root = ObjectIdentity("IF-MIB", "ifDescr")
    query = [ObjectType(root)]
    while True:
        error_indication, error_status, error_index, var_binds = await bulkCmd(
            snmp_engine,
            CommunityData(args.community, mpModel=1),
            UdpTransportTarget((args.agent, 161)),
            ContextData(),
            0,
            50,
            *query,
            lexicographicMode=False,
        )

        if error_indication:
            _log.error(error_indication)
            break

        elif error_status:
            _log.error("%s at %s", error_status.prettyPrint(), error_index and query[int(error_index) - 1][0] or "?")
        else:
            for row in var_binds:
                for var_bind in row:
                    # this break is only necessary if the query is translated to a get-next command on a v1 session
                    if not root.getOid().isPrefixOf(var_bind[0]):
                        break
                    _log.info(" = ".join([x.prettyPrint() for x in var_bind]))
        query = var_binds[-1]
        # this break is only necessary if the query is translated to a get-next command on a v1 session
        if not root.getOid().isPrefixOf(query[0][0]):
            break

        if isEndOfMib(query):
            break

    snmp_engine.transportDispatcher.closeDispatcher()


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch ifDescr values from an SNMP agent")
    parser.add_argument("agent", type=str, help="SNMP agent name/address")
    parser.add_argument(
        "-c",
        "--community",
        type=str,
        metavar="COMMUNITY",
        default="public",
        help="SNMP community to use (if not `public`)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
