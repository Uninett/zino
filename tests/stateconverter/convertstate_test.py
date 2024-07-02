import os
from datetime import datetime, timedelta
from ipaddress import ip_address

import pytest

from zino.stateconverter.convertstate import create_state
from zino.statemodels import (
    AlarmEvent,
    BFDEvent,
    BFDSessState,
    BGPAdminStatus,
    BGPEvent,
    BGPOperState,
    EventState,
    InterfaceState,
    PortStateEvent,
)


def test_state_can_be_parsed_without_crashing(save_state_path):
    state = create_state(save_state_path)
    assert state


def test_bfd_event_is_created_correctly(save_state_path):
    state = create_state(save_state_path)
    event = state.events.checkout(200)
    assert isinstance(event, BFDEvent)
    assert event.type == "bfd"
    assert event.bfdaddr == ip_address("219.188.192.78")
    assert event.bfddiscr == 4500
    assert event.bfdix == 30
    assert event.bfdstate == BFDSessState.DOWN
    assert len(event.history) == 1
    assert len(event.log) == 1
    assert event.lastevent == "changed from up to adminDown (poll)"
    assert event.opened == datetime.fromtimestamp(1700400123)
    assert event.polladdr == ip_address("93.150.77.115")
    assert event.priority == 100
    assert event.router == "blaafjell-gw2"
    assert event.state == EventState.OPEN
    assert event.updated == datetime.fromtimestamp(1700400123)


def test_alarm_event_is_created_correctly(save_state_path):
    state = create_state(save_state_path)
    event = state.events.checkout(146)
    assert isinstance(event, AlarmEvent)
    assert event.type == "alarm"
    assert event.alarm_type == "yellow"
    assert event.alarm_count == 1
    assert len(event.history) == 2
    assert len(event.log) == 2
    assert event.lastevent == "alarms went from 0 to 1"
    assert event.opened == datetime.fromtimestamp(1696257668)
    assert event.polladdr == ip_address("176.53.125.80")
    assert event.priority == 300
    assert event.router == "whoville-gw1"
    assert event.state == EventState.WAITING
    assert event.updated == datetime.fromtimestamp(1696257668)


def test_portstate_event_is_created_correctly(save_state_path):
    state = create_state(save_state_path)
    event = state.events.checkout(110)
    assert isinstance(event, PortStateEvent)
    assert event.type == "portstate"
    assert event.ifindex == 150
    assert event.descr == "LACP-link, test.no-phy1"
    assert event.ac_down == timedelta(seconds=15000000)
    assert len(event.history) == 1
    assert len(event.log) == 1
    assert event.opened == datetime.fromtimestamp(1686257668)
    assert event.polladdr == ip_address("53.44.228.67")
    assert event.port == "ge-1/0/10"
    assert event.portstate == InterfaceState.UP
    assert event.priority == 100
    assert event.router == "arkham-sw1"
    assert event.state == EventState.IGNORED
    assert event.updated == datetime.fromtimestamp(1686257668)


def test_bgp_event_is_created_correctly(save_state_path):
    """Placeholder for when BGP is supported"""
    state = create_state(save_state_path)
    event = state.events.checkout(100)
    assert isinstance(event, BGPEvent)
    assert event.type == "bgp"
    assert event.router == "auroralane-gw1"
    assert event.state == EventState.WAITING
    assert event.polladdr == ip_address("219.188.192.78")
    assert event.opened == datetime.fromtimestamp(1706257668)
    assert event.updated == datetime.fromtimestamp(1706257668)
    assert event.priority == 100
    assert len(event.history) == 1
    assert len(event.log) == 1
    assert event.lastevent == "peer is down"
    assert event.remote_addr == ip_address("0515:7cfd:1bcc:279e:f5a4:5528:f4c3:58af")
    assert event.remote_as == 100
    assert event.peer_uptime == 420
    assert event.bgpos == BGPOperState.DOWN
    assert event.bgpas == BGPAdminStatus.RUNNING


def test_jnx_alarms_are_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("whoville-gw1")
    assert device.alarms["yellow"] == 1
    assert device.alarms["red"] == 0


def test_bfd_sess_addr_is_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("blaafjell-gw2")
    device.ports[30].bfd_state.session_addr is None


def test_bfd_sess_discr_is_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("blaafjell-gw2")
    device.ports[30].bfd_state.session_discr == 0


def test_bfd_sess_state_is_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("blaafjell-gw2")
    device.ports[30].bfd_state.session_state == BFDSessState.DOWN


def test_juniper_devices_are_registered_as_juniper(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("juniper-gw1")
    assert device.is_juniper


def test_cisco_devices_are_registered_as_cisco(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("cisco-gw1")
    assert device.is_cisco


def test_portstate_is_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("arkham-sw1")
    assert device.ports[150].state == InterfaceState.UP


def test_ifdescr_is_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("arkham-sw1")
    assert device.ports[150].ifdescr == "ge-1/0/10"


def test_ifalias_is_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("arkham-sw1")
    assert device.ports[150].ifalias == "LACP-link, test.no-phy1"


def test_bgp_uptime_is_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("auroralane-gw1")
    ip = ip_address("3000:04AB:0554:0001:0000:0000:0000:00AA")
    assert device.bgp_peers[ip].uptime == 14000000


def test_bgp_admin_status_is_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("auroralane-gw1")
    ip = ip_address("3000:04AB:0554:0001:0000:0000:0000:00AA")
    assert device.bgp_peers[ip].admin_status == BGPAdminStatus.RUNNING


def test_bgp_oper_status_is_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("auroralane-gw1")
    ip = ip_address("3000:04AB:0554:0001:0000:0000:0000:00AA")
    assert device.bgp_peers[ip].oper_state == BGPOperState.ACTIVE


def test_bgp_peers_is_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("auroralane-gw1")
    ip = ip_address("3000:04AB:0554:0001:0000:0000:0000:00AA")
    assert ip in device.bgp_peers
    assert len(device.bgp_peers) == 1


def test_invalid_event_attribute_should_not_be_set(invalid_event_save_state_path):
    state = create_state(invalid_event_save_state_path)
    event = state.events.checkout(100)
    assert not hasattr(event, "invalid_attr")


def test_addresses_should_be_set(save_state_path):
    state = create_state(save_state_path)
    ip = ip_address("175.46.88.27")
    assert state.addresses[ip] == "boot-gw1"


@pytest.fixture
def save_state_path():
    this_directory = os.path.dirname(__file__)
    state_file = os.path.join(this_directory, "tcl_fixtures", "zino1_state.tcl")
    return state_file


@pytest.fixture
def invalid_event_save_state_path():
    this_directory = os.path.dirname(__file__)
    state_file = os.path.join(this_directory, "tcl_fixtures", "zino1_state_invalid_event_attr.tcl")
    return state_file
