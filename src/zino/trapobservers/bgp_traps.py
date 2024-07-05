"""This module implements BGP trap handling.

Examples of how to send test traps:

snmptrap -v 2c -c public localhost:1162 "" \
    BGP4-V2-MIB-JUNIPER::jnxBgpM2BackwardTransition \
    BGP4-V2-MIB-JUNIPER::jnxBgpM2PeerLocalAddrType i 1 \
    BGP4-V2-MIB-JUNIPER::jnxBgpM2PeerLocalAddr x "0A000002" \
    BGP4-V2-MIB-JUNIPER::jnxBgpM2PeerRemoteAddrType i 1 \
    BGP4-V2-MIB-JUNIPER::jnxBgpM2PeerRemoteAddr x "0A000001" \
    BGP4-V2-MIB-JUNIPER::jnxBgpM2PeerLastErrorReceived x "0102" \
    BGP4-V2-MIB-JUNIPER::jnxBgpM2PeerState i 4

This sends all the variables required by the MIB, but this trap observer only cares about the remote peer address and
the peer state value.

"""

import logging
from ipaddress import ip_address
from typing import Optional, Tuple

from zino.statemodels import BGPOperState, BGPPeerSession, IPAddress
from zino.trapd import TrapMessage, TrapObserver

_logger = logging.getLogger(__name__)


class BgpTrapObserver(TrapObserver):
    """Handles BGP peering session operational transition messages"""

    WANTED_TRAPS = {
        ("BGP4-V2-MIB-JUNIPER", "jnxBgpM2BackwardTransition"),
        ("BGP4-V2-MIB-JUNIPER", "jnxBgpM2Established"),
    }

    def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        try:
            peer, state = self._pre_parse_trap(trap)
        except MissingRequiredTrapVariables:
            return
        except ValueError as error:
            _logger.warning(error)
            return

        if trap.name == "jnxBgpM2BackwardTransition":
            self.handle_backward_transition(trap, peer, state)
        elif trap.name == "jnxBgpM2Established":
            self.handle_established(trap, peer, state)
        else:
            # Something weird happened, let someone else handle it
            _logger.info("%s: Unknown trap received: %s", trap.agent.device.name, trap.name)
            return True

    def handle_backward_transition(self, trap: TrapMessage, peer: IPAddress, state: BGPOperState):
        _logger.debug("BGP backward transition trap received: %r", trap)
        bgp_peers = trap.agent.device.bgp_peers
        prev_state = bgp_peers[peer].oper_state if peer in bgp_peers else "unknown"

        if state != BGPOperState.ESTABLISHED and prev_state == BGPOperState.ESTABLISHED:
            _logger.info("%s Lost BGP peer: %s state %s", trap.agent.device.name, peer, state)

        bgp_peers.setdefault(peer, BGPPeerSession()).oper_state = state

    def handle_established(self, trap: TrapMessage, peer: IPAddress, state: BGPOperState):
        _logger.debug("BGP established trap received: %r", trap)
        # TODO Zino 1 does not actually update the internal peering state here, we should verify that this is really
        #  the desired behavior
        _logger.info("%s BGP peer up: %s state %s", trap.agent.device.name, peer, state)

    def _pre_parse_trap(self, trap: TrapMessage) -> Tuple[IPAddress, BGPOperState]:
        if "jnxBgpM2PeerLocalAddrType" not in trap.variables:
            raise MissingRequiredTrapVariables()

        try:
            remote_addr = bytes(trap.variables["jnxBgpM2PeerRemoteAddr"].raw_value)
            peer = ip_address(remote_addr)
        except ValueError:
            raise ValueError(f"BGP transition trap received with invalid peer address: {remote_addr!r}")

        try:
            raw_state = trap.variables["jnxBgpM2PeerState"].value
            state = BGPOperState(raw_state)
        except ValueError:
            raise ValueError(f"BGP transition trap received with invalid peer state: {raw_state}")

        return peer, state


class MissingRequiredTrapVariables(ValueError):
    pass
