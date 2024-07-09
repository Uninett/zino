import os
from datetime import datetime, timedelta, timezone
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
    MatchType,
    PortStateEvent,
    PortStateMaintenance,
)


def test_state_should_be_parsed_without_crashing(save_state_path):
    state = create_state(save_state_path)
    assert state


class TestEvents:
    def test_bfd_event_should_be_created_correctly(self, save_state_path):
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
        assert event.opened == datetime.fromtimestamp(1700400123, tz=timezone.utc)
        assert event.polladdr == ip_address("93.150.77.115")
        assert event.priority == 100
        assert event.router == "blaafjell-gw2"
        assert event.state == EventState.OPEN
        assert event.updated == datetime.fromtimestamp(1700400123, tz=timezone.utc)
        assert event.neigh_rdns == "nissen.nordpolen.no"

    def test_alarm_event_should_be_created_correctly(self, save_state_path):
        state = create_state(save_state_path)
        event = state.events.checkout(146)
        assert isinstance(event, AlarmEvent)
        assert event.type == "alarm"
        assert event.alarm_type == "yellow"
        assert event.alarm_count == 1
        assert len(event.history) == 2
        assert len(event.log) == 2
        assert event.lastevent == "alarms went from 0 to 1"
        assert event.opened == datetime.fromtimestamp(1696257668, tz=timezone.utc)
        assert event.polladdr == ip_address("176.53.125.80")
        assert event.priority == 300
        assert event.router == "whoville-gw1"
        assert event.state == EventState.WAITING
        assert event.updated == datetime.fromtimestamp(1696257668, tz=timezone.utc)

    def test_portstate_event_should_be_created_correctly(self, save_state_path):
        state = create_state(save_state_path)
        event = state.events.checkout(110)
        assert isinstance(event, PortStateEvent)
        assert event.type == "portstate"
        assert event.ifindex == 150
        assert event.descr == "LACP-link, test.no-phy1"
        assert event.ac_down == timedelta(seconds=15000000)
        assert len(event.history) == 1
        assert len(event.log) == 1
        assert event.opened == datetime.fromtimestamp(1686257668, tz=timezone.utc)
        assert event.polladdr == ip_address("53.44.228.67")
        assert event.port == "ge-1/0/10"
        assert event.portstate == InterfaceState.UP
        assert event.priority == 100
        assert event.router == "arkham-sw1"
        assert event.state == EventState.IGNORED
        assert event.updated == datetime.fromtimestamp(1686257668, tz=timezone.utc)

    def test_bgp_event_should_be_created_correctly(self, save_state_path):
        """Placeholder for when BGP is supported"""
        state = create_state(save_state_path)
        event = state.events.checkout(100)
        assert isinstance(event, BGPEvent)
        assert event.type == "bgp"
        assert event.router == "auroralane-gw1"
        assert event.state == EventState.WAITING
        assert event.polladdr == ip_address("219.188.192.78")
        assert event.opened == datetime.fromtimestamp(1706257668, tz=timezone.utc)
        assert event.updated == datetime.fromtimestamp(1706257668, tz=timezone.utc)
        assert event.priority == 100
        assert len(event.history) == 1
        assert len(event.log) == 1
        assert event.lastevent == "peer is down"
        assert event.remote_addr == ip_address("0515:7cfd:1bcc:279e:f5a4:5528:f4c3:58af")
        assert event.remote_as == 100
        assert event.peer_uptime == 420
        assert event.bgpos == BGPOperState.DOWN
        assert event.bgpas == BGPAdminStatus.RUNNING

    def test_invalid_event_attribute_should_not_be_set(self, invalid_event_save_state_path):
        state = create_state(invalid_event_save_state_path)
        event = state.events.checkout(100)
        assert not hasattr(event, "invalid_attr")


def test_jnx_alarms_should_be_set_correctly(save_state_path):
    state = create_state(save_state_path)
    device = state.devices.get("whoville-gw1")
    assert device.alarms["yellow"] == 1
    assert device.alarms["red"] == 0


class TestBFD:
    def test_sess_addr_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("blaafjell-gw2")
        device.ports[30].bfd_state.session_addr is None

    def test_sess_discr_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("blaafjell-gw2")
        device.ports[30].bfd_state.session_discr == 0

    def test_sess_state_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("blaafjell-gw2")
        device.ports[30].bfd_state.session_state == BFDSessState.DOWN


class TestVendor:
    def test_juniper_device_should_be_registered_as_juniper(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("juniper-gw1")
        assert device.is_juniper

    def test_cisco_device_should_be_registered_as_cisco(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("cisco-gw1")
        assert device.is_cisco


class TestPort:
    def test_portstate_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("arkham-sw1")
        assert device.ports[150].state == InterfaceState.UP

    def test_ifdescr_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("arkham-sw1")
        assert device.ports[150].ifdescr == "ge-1/0/10"

    def test_ifalias_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("arkham-sw1")
        assert device.ports[150].ifalias == "LACP-link, test.no-phy1"


class TestBGP:
    def test_uptime_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("auroralane-gw1")
        ip = ip_address("3000:04AB:0554:0001:0000:0000:0000:00AA")
        assert device.bgp_peers[ip].uptime == 14000000

    def test_admin_status_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("auroralane-gw1")
        ip = ip_address("3000:04AB:0554:0001:0000:0000:0000:00AA")
        assert device.bgp_peers[ip].admin_status == BGPAdminStatus.RUNNING

    def test_oper_status_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("auroralane-gw1")
        ip = ip_address("3000:04AB:0554:0001:0000:0000:0000:00AA")
        assert device.bgp_peers[ip].oper_state == BGPOperState.ACTIVE

    def test_peers_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        device = state.devices.get("auroralane-gw1")
        ip = ip_address("3000:04AB:0554:0001:0000:0000:0000:00AA")
        assert ip in device.bgp_peers
        assert len(device.bgp_peers) == 1


class TestPM:
    def test_pm_should_be_created_correctly(self, save_state_path):
        state = create_state(save_state_path)
        pm = state.planned_maintenances[3188]
        assert isinstance(pm, PortStateMaintenance)
        assert pm.type == "portstate"
        assert pm.start_time == datetime.fromtimestamp(1720021526, tz=timezone.utc)
        assert pm.end_time == datetime.fromtimestamp(1720025126, tz=timezone.utc)
        assert pm.match_type == MatchType.INTF_REGEXP
        assert pm.match_expression == "ge-1/0/10"
        assert pm.match_device == "blaafjell-gw2"
        assert pm.event_ids == [110]
        assert len(pm.log) == 1

    def test_last_pm_id_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        assert state.planned_maintenances.last_pm_id == 3188

    def test_last_run_should_be_set_correctly(self, save_state_path):
        state = create_state(save_state_path)
        assert state.planned_maintenances.last_run == datetime.fromtimestamp(1720018082, tz=timezone.utc)


def test_addresses_should_be_set_correctly(save_state_path):
    state = create_state(save_state_path)
    ip = ip_address("175.46.88.27")
    assert state.addresses[ip] == "boot-gw1"


@pytest.fixture
def save_state_path():
    this_directory = os.path.dirname(__file__)
    state_file = os.path.join(this_directory, "fixtures", "zino1_state.tcl")
    return state_file


@pytest.fixture
def invalid_event_save_state_path():
    this_directory = os.path.dirname(__file__)
    state_file = os.path.join(this_directory, "fixtures", "zino1_state_invalid_event_attr.tcl")
    return state_file
