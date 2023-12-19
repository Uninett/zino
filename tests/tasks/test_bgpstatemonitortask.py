import logging
from ipaddress import IPv4Address

import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.statemodels import BGPEvent
from zino.tasks.bgpstatemonitortask import BgpStateMonitorTask

DEVICE_NAME = "buick.lab.example.org"
DEVICE_ADDRESS = "127.0.0.1"


class TestBgpStateMonitorTask:
    @pytest.mark.asyncio
    async def test_task_for_non_bgp_router_runs_without_errors(self, non_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(non_bgp_device, state)

        assert (await task.run()) is None

    @pytest.mark.asyncio
    async def test_task_juniper_runs_without_errors(self, juniper_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(juniper_bgp_device, state)
        assert (await task.run()) is None

    @pytest.mark.asyncio
    async def test_task_cisco_runs_without_errors(self, cisco_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(cisco_bgp_device, state)
        assert (await task.run()) is None

    @pytest.mark.asyncio
    async def test_task_general_runs_without_errors(self, general_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(general_bgp_device, state)
        assert (await task.run()) is None

    @pytest.mark.asyncio
    async def test_task_logs_missing_information(self, snmpsim, snmp_test_port, caplog):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="missing-info-bgp",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        with caplog.at_level(logging.INFO):
            await task.run()

        assert f"router {device.name} misses BGP variables" in caplog.text

    @pytest.mark.asyncio
    async def test_peer_admin_status_changing_to_stop_while_peer_state_is_not_established_should_create_event(
        self, snmpsim, snmp_test_port
    ):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="general-bgp-admin-down",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("127.0.0.1")
        # set initial state
        task.device_state.bgp_peer_admin_states = {peer_address: "start"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "stop"
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event

    @pytest.mark.asyncio
    async def test_remote_as_different_from_local_as_changing_oper_state_to_down_should_create_event(
        self, snmpsim, snmp_test_port
    ):
        """Tests that an event should be made if a BGP connection to a device that is in a different AS
        than the local AS for this device reports that their oper_state has changed from established to
        something else
        """
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="general-bgp-oper-down",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("127.0.0.1")
        # set initial state
        task.device_state.bgp_peer_oper_states = {peer_address: "established"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event


class TestGetBgpType:
    @pytest.mark.asyncio
    async def test_get_bgp_type_returns_correct_type_for_juniper(self, juniper_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(juniper_bgp_device, state)
        assert (await task._get_bgp_style()) == "juniper"

    @pytest.mark.asyncio
    async def test_get_bgp_type_returns_correct_type_for_cisco(self, cisco_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(cisco_bgp_device, state)
        assert (await task._get_bgp_style()) == "cisco"

    @pytest.mark.asyncio
    async def test_get_bgp_type_returns_correct_type_for_general(self, general_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(general_bgp_device, state)
        assert (await task._get_bgp_style()) == "general"

    @pytest.mark.asyncio
    async def test_get_bgp_type_returns_correct_type_for_non_bgp_device(self, non_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(non_bgp_device, state)
        assert (await task._get_bgp_style()) is None


@pytest.fixture()
def cisco_bgp_device(snmpsim, snmp_test_port):
    device = PollDevice(
        name="buick.lab.example.org",
        address=DEVICE_ADDRESS,
        community="cisco-bgp",
        port=snmp_test_port,
    )
    yield device


@pytest.fixture()
def juniper_bgp_device(snmpsim, snmp_test_port):
    device = PollDevice(
        name=DEVICE_NAME,
        address=DEVICE_ADDRESS,
        community="juniper-bgp",
        port=snmp_test_port,
    )
    yield device


@pytest.fixture()
def general_bgp_device(snmpsim, snmp_test_port):
    device = PollDevice(
        name=DEVICE_NAME,
        address=DEVICE_ADDRESS,
        community="general-bgp",
        port=snmp_test_port,
    )
    yield device


@pytest.fixture()
def non_bgp_device(snmpsim, snmp_test_port):
    device = PollDevice(
        name=DEVICE_NAME,
        address=DEVICE_ADDRESS,
        community="public",
        port=snmp_test_port,
    )
    yield device
