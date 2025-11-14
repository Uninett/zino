"""SNMP agent for Zino that responds to uptime queries.

This module implements an SNMP agent that listens on a configurable port
and responds to queries for ZINO-MIB::zinoUpTime, which is used by clients
for failover detection.

The agent is built on PySNMP, since the netsnmpy library does not yet provide
support for setting up SNMP agents - and performance optimizations for many
parallel conversations are not needed here.
"""

import asyncio
import logging
import os
import time
from ipaddress import IPv6Address, ip_address
from typing import Optional

from pysnmp.carrier.asyncio.dgram import udp, udp6
from pysnmp.carrier.asyncio.dispatch import AsyncioDispatcher
from pysnmp.entity import config, engine
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.smi import builder

_log = logging.getLogger(__name__)


class ZinoSnmpAgent:
    """SNMP agent that responds to queries for Zino uptime.

    This agent is used by clients like EMT for failover detection.
    It responds to SNMP GET requests for the ZINO-MIB::zinoUpTime object.
    """

    def __init__(
        self,
        listen_address: str = "0.0.0.0",
        listen_port: int = 8000,
        community: Optional[str] = None,
        start_time: Optional[float] = None,
    ):
        """Initialize the SNMP agent.

        :param listen_address: IP address to bind to (default: "0.0.0.0")
        :param listen_port: Port to listen on (default: 8000)
        :param community: SNMP community string (default: None, accepts any)
        :param start_time: Server start timestamp (default: current time)
        """
        self.listen_address = listen_address
        self.listen_port = listen_port
        self.community = community or "public"
        self.start_time = start_time or time.time()
        self.snmp_engine = None
        self.transport_dispatcher = None
        self._running = False

    def _setup_engine(self):
        """Sets up the SNMP engine with configuration."""
        # Create SNMP engine
        self.snmp_engine = engine.SnmpEngine()

        # Configure transport (UDP/IPv4 and IPv6)
        self.transport_dispatcher = AsyncioDispatcher()
        self.snmp_engine.registerTransportDispatcher(self.transport_dispatcher)

        # Determine if we need IPv4 or IPv6 transport
        try:
            addr = ip_address(self.listen_address)
            if isinstance(addr, IPv6Address):
                transport = udp6.Udp6AsyncioTransport()
                endpoint = (self.listen_address, self.listen_port)
            else:
                transport = udp.UdpAsyncioTransport()
                endpoint = (self.listen_address, self.listen_port)
        except ValueError:
            # If address is a hostname, default to IPv4
            transport = udp.UdpAsyncioTransport()
            endpoint = (self.listen_address, self.listen_port)

        # Open the transport - this actually binds to the socket
        transport = transport.openServerMode(endpoint)

        # Add transport to the engine
        config.addTransport(self.snmp_engine, udp.domainName, transport)

        # Configure SNMPv1 and SNMPv2c
        config.addV1System(self.snmp_engine, "zino-agent", self.community)

        # Configure vacm to allow access
        config.addVacmUser(self.snmp_engine, 2, "zino-agent", "noAuthNoPriv", (), (), ())  # SNMPv2c
        config.addVacmUser(self.snmp_engine, 1, "zino-agent", "noAuthNoPriv", (), (), ())  # SNMPv1

        # Get MIB controller and builder
        mib_instrum = self.snmp_engine.msgAndPduDsp.mibInstrumController
        mib_builder = mib_instrum.mibBuilder

        # Add the mibdumps directory to the MIB search path
        mibdumps_dir = os.path.join(os.path.dirname(__file__), "mibdumps")
        mib_builder.addMibSources(builder.DirMibSource(mibdumps_dir))

        # Load the required MIB modules
        mib_builder.loadModules("SNMPv2-MIB", "UNINETT-SMI", "ZINO-MIB")

        # Register the zinoUpTime scalar with dynamic value
        self._register_zino_uptime(mib_instrum)

        # Register SNMP command responders for GET and GETNEXT
        snmp_context = context.SnmpContext(self.snmp_engine)
        cmdrsp.GetCommandResponder(self.snmp_engine, snmp_context)
        cmdrsp.NextCommandResponder(self.snmp_engine, snmp_context)

        _log.debug("SNMP agent configured on %s:%d", self.listen_address, self.listen_port)

    def _register_zino_uptime(self, mib_instrum):
        """Registers zinoUpTime MIB object with dynamic uptime calculation."""
        mib_builder = mib_instrum.mibBuilder

        # Import zinoUpTime from loaded MIB and MibScalarInstance
        (zino_uptime,) = mib_builder.importSymbols("ZINO-MIB", "zinoUpTime")
        (MibScalarInstance,) = mib_builder.importSymbols("SNMPv2-SMI", "MibScalarInstance")

        # Create custom instance that returns current uptime
        class UptimeInstance(MibScalarInstance):
            def readGet(self, name, val, idx, acInfo):
                return name, self.syntax.clone(self._get_uptime())

        # Register the dynamic instance
        instance = UptimeInstance(zino_uptime.getName(), (0,), zino_uptime.getSyntax())
        instance._get_uptime = self._get_uptime  # Bind the uptime method

        mib_builder.exportSymbols("__UPTIME__", zinoUpTimeInstance=instance)
        mib_builder.loadModules("__UPTIME__")

    def _get_uptime(self) -> int:
        """Calculates uptime in seconds since instance was created."""
        return int(time.time() - self.start_time)

    async def open(self):
        """Opens the SNMP agent port and start serving SNMP requests."""
        if self._running:
            _log.warning("SNMP agent is already running")
            return

        try:
            self._setup_engine()
            self._running = True
            _log.info("SNMP agent started on %s:%d", self.listen_address, self.listen_port)
        except Exception as error:
            _log.error("Failed to start SNMP agent: %s", error)
            self._running = False
            raise

    def close(self):
        """Closes the port and stop the SNMP agent."""
        if not self._running:
            return

        _log.info("Stopping SNMP agent")
        if self.transport_dispatcher:
            self.transport_dispatcher.closeDispatcher()
        if self.snmp_engine:
            self.snmp_engine.transportDispatcher.closeDispatcher()
        self._running = False


def main():
    """Run the SNMP agent standalone for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Zino SNMP Agent")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--community", default=None, help="SNMP community string (default: accept any)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        _log.setLevel(logging.DEBUG)

    agent = ZinoSnmpAgent(listen_address=args.host, listen_port=args.port, community=args.community)

    print(f"Starting SNMP agent on {args.host}:{args.port}")
    print(f"Community: {args.community if args.community else 'any'}")
    print("OID: ZINO-MIB::zinoUpTime")
    print("Press Ctrl+C to stop...")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(agent.open())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("\nStopping agent...")
        agent.close()
    finally:
        loop.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
