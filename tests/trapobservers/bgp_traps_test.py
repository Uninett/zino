import ipaddress
import logging
from unittest.mock import Mock

import pytest

from zino.statemodels import BGPOperState, BGPPeerSession
from zino.trapd import TrapMessage
from zino.trapobservers.bgp_traps import BgpTrapObserver


class TestBgpTrapObserver:
    @pytest.mark.asyncio
    async def test_when_backward_transition_trap_is_received_it_should_change_bgp_peer_state(
        self, backward_transition_trap
    ):
        device = backward_transition_trap.agent.device
        peer = next(iter(device.bgp_peers.keys()))

        observer = BgpTrapObserver(state=Mock())
        await observer.handle_trap(trap=backward_transition_trap)

        assert len(device.bgp_peers) == 1
        assert device.bgp_peers[peer].oper_state == BGPOperState.ACTIVE

    def test_when_trap_is_missing_required_varbinds_it_should_do_nothing(self, backward_transition_trap):
        """jnxBgpM2PeerLocalAddrType is required to be present, according to legacy Zino"""
        device = backward_transition_trap.agent.device
        peer = next(iter(device.bgp_peers.keys()))
        backward_transition_trap.variables.pop("jnxBgpM2PeerLocalAddrType")

        observer = BgpTrapObserver(state=Mock())
        observer.handle_trap(trap=backward_transition_trap)

        assert len(device.bgp_peers) == 1
        assert device.bgp_peers[peer].oper_state == BGPOperState.ESTABLISHED

    def test_when_trap_has_invalid_remote_addr_it_should_do_nothing(self, backward_transition_trap):
        device = backward_transition_trap.agent.device
        peer = next(iter(device.bgp_peers.keys()))
        backward_transition_trap.variables["jnxBgpM2PeerRemoteAddr"] = Mock(
            var="jnxBgpM2PeerLocalAddr", raw_value=b"INVALID"
        )

        observer = BgpTrapObserver(state=Mock())
        observer.handle_trap(trap=backward_transition_trap)

        assert len(device.bgp_peers) == 1
        assert device.bgp_peers[peer].oper_state == BGPOperState.ESTABLISHED

    def test_when_trap_has_invalid_oper_state_it_should_do_nothing(self, backward_transition_trap):
        device = backward_transition_trap.agent.device
        peer = next(iter(device.bgp_peers.keys()))
        backward_transition_trap.variables["jnxBgpM2PeerState"] = Mock(var="jnxBgpM2PeerState", value="INVALIDFOOBAR")

        observer = BgpTrapObserver(state=Mock())
        observer.handle_trap(trap=backward_transition_trap)

        assert len(device.bgp_peers) == 1
        assert device.bgp_peers[peer].oper_state == BGPOperState.ESTABLISHED

    @pytest.mark.asyncio
    async def test_when_established_trap_is_received_it_should_just_log_it(self, established_trap, caplog):
        """This requirement is disputed until Håvard E confirms it"""
        observer = BgpTrapObserver(state=Mock())
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=established_trap)
            assert "BGP peer up" in caplog.text

    def test_when_trap_is_unknown_it_should_pass_it_on(self, established_trap):
        established_trap.name = "FOOBAR"
        observer = BgpTrapObserver(state=Mock())
        assert observer.handle_trap(trap=established_trap)


@pytest.fixture
def backward_transition_trap(localhost_trap_originator) -> TrapMessage:
    """Returns a correct backward transition trap with internal state to match"""
    peer = ipaddress.IPv4Address("10.0.0.1")
    localhost_trap_originator.device.bgp_peers = {peer: BGPPeerSession(oper_state=BGPOperState.ESTABLISHED)}

    trap = TrapMessage(agent=localhost_trap_originator, mib="BGP4-V2-MIB-JUNIPER", name="jnxBgpM2BackwardTransition")
    trap.variables = {
        "jnxBgpM2PeerLocalAddrType": Mock(var="jnxBgpM2PeerLocalAddrType", value=1),
        "jnxBgpM2PeerRemoteAddrType": Mock(var="jnxBgpM2PeerLocalAddrType", value=1),
        "jnxBgpM2PeerRemoteAddr": Mock(var="jnxBgpM2PeerLocalAddr", raw_value=peer.packed),
        "jnxBgpM2PeerState": Mock(var="jnxBgpM2PeerState", value="active"),
    }
    return trap


@pytest.fixture
def established_trap(localhost_trap_originator) -> TrapMessage:
    """Returns a correct established trap with internal state to match"""
    peer = ipaddress.IPv4Address("10.0.0.1")
    localhost_trap_originator.device.bgp_peers = {peer: BGPPeerSession(oper_state=BGPOperState.ACTIVE)}

    trap = TrapMessage(agent=localhost_trap_originator, mib="BGP4-V2-MIB-JUNIPER", name="jnxBgpM2Established")
    trap.variables = {
        "jnxBgpM2PeerLocalAddrType": Mock(var="jnxBgpM2PeerLocalAddrType", value=1),
        "jnxBgpM2PeerRemoteAddrType": Mock(var="jnxBgpM2PeerLocalAddrType", value=1),
        "jnxBgpM2PeerRemoteAddr": Mock(var="jnxBgpM2PeerLocalAddr", raw_value=peer.packed),
        "jnxBgpM2PeerState": Mock(var="jnxBgpM2PeerState", value="established"),
    }
    return trap
