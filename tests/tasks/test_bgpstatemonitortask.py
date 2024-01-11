import logging
from ipaddress import IPv4Address, IPv6Address

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
    async def test_external_reset_general_creates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="general-bgp-external-reset",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_up_times = {peer_address: 5000}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "start"
        assert task.device_state.bgp_peer_oper_states[peer_address] == "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "start"
        assert event.operational_state == "established"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 250

    @pytest.mark.asyncio
    async def test_external_reset_cisco_creates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="cisco-bgp-external-reset",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_up_times = {peer_address: 5000}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "start"
        assert task.device_state.bgp_peer_oper_states[peer_address] == "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "start"
        assert event.operational_state == "established"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 250

    @pytest.mark.asyncio
    async def test_external_reset_juniper_creates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="juniper-bgp-external-reset",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_up_times = {peer_address: 5000}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "running"
        assert task.device_state.bgp_peer_oper_states[peer_address] == "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "running"
        assert event.operational_state == "established"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 250

    @pytest.mark.asyncio
    async def test_session_up_general_updates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="general-bgp-external-reset",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # create admin down event
        event, _ = state.events.get_or_create_event(device_name=device.name, port=peer_address, event_class=BGPEvent)
        event.operational_state = "down"
        event.admin_status = "stop"
        event.remote_address = peer_address
        event.remote_as = 20
        event.peer_uptime = 0

        await task.run()

        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "start"
        assert task.device_state.bgp_peer_oper_states[peer_address] == "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "start"
        assert event.operational_state == "established"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 250

    @pytest.mark.asyncio
    async def test_session_up_cisco_updates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="cisco-bgp-external-reset",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # create admin down event
        event, _ = state.events.get_or_create_event(device_name=device.name, port=peer_address, event_class=BGPEvent)
        event.operational_state = "down"
        event.admin_status = "stop"
        event.remote_address = peer_address
        event.remote_as = 20
        event.peer_uptime = 0

        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "start"
        assert task.device_state.bgp_peer_oper_states[peer_address] == "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "start"
        assert event.operational_state == "established"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 250

    @pytest.mark.asyncio
    async def test_session_up_juniper_updates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="juniper-bgp-external-reset",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # create admin down event
        event, _ = state.events.get_or_create_event(device_name=device.name, port=peer_address, event_class=BGPEvent)
        event.operational_state = "down"
        event.admin_status = "halted"
        event.remote_address = peer_address
        event.remote_as = 20
        event.peer_uptime = 0

        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "running"
        assert task.device_state.bgp_peer_oper_states[peer_address] == "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "running"
        assert event.operational_state == "established"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 250

    @pytest.mark.asyncio
    async def test_admin_down_general_creates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="general-bgp-admin-down",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_admin_states = {peer_address: "start"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "stop"
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "stop"
        assert event.operational_state == "down"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 0

    @pytest.mark.asyncio
    async def test_admin_down_cisco_creates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="cisco-bgp-admin-down",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_admin_states = {peer_address: "start"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "stop"
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "stop"
        assert event.operational_state == "down"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 0

    @pytest.mark.asyncio
    async def test_admin_down_juniper_creates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="juniper-bgp-admin-down",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_admin_states = {peer_address: "running"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "halted"
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "halted"
        assert event.operational_state == "down"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 0

    @pytest.mark.asyncio
    async def test_admin_up_general_creates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="general-bgp-admin-up",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_admin_states = {peer_address: "stop"}
        task.device_state.bgp_peer_oper_states = {peer_address: "idle"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "start"
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "start"
        assert event.operational_state == "idle"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 0

    @pytest.mark.asyncio
    async def test_admin_up_cisco_creates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="cisco-bgp-admin-up",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_admin_states = {peer_address: "stop"}
        task.device_state.bgp_peer_oper_states = {peer_address: "idle"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "start"
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "start"
        assert event.operational_state == "idle"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 0

    @pytest.mark.asyncio
    async def test_admin_up_juniper_creates_event(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="juniper-bgp-admin-up",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_admin_states = {peer_address: "halted"}
        task.device_state.bgp_peer_oper_states = {peer_address: "idle"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_admin_states[peer_address] == "running"
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "running"
        assert event.operational_state == "idle"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 0

    @pytest.mark.asyncio
    async def test_oper_down_general_creates_event(self, snmpsim, snmp_test_port):
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
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_admin_states = {peer_address: "start"}
        task.device_state.bgp_peer_oper_states = {peer_address: "established"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "start"
        assert event.operational_state == "down"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 1000000

    @pytest.mark.asyncio
    async def test_oper_down_cisco_creates_event(self, snmpsim, snmp_test_port):
        """Tests that an event should be made if a BGP connection to a device that is in a different AS
        than the local AS for this device reports that their oper_state has changed from established to
        something else
        """
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="cisco-bgp-oper-down",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_admin_states = {peer_address: "start"}
        task.device_state.bgp_peer_oper_states = {peer_address: "established"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "start"
        assert event.operational_state == "down"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 1000000

    @pytest.mark.asyncio
    async def test_oper_down_juniper_creates_event(self, snmpsim, snmp_test_port):
        """Tests that an event should be made if a BGP connection to a device that is in a different AS
        than the local AS for this device reports that their oper_state has changed from established to
        something else
        """
        device = PollDevice(
            name=DEVICE_NAME,
            address=DEVICE_ADDRESS,
            community="juniper-bgp-oper-down",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = BgpStateMonitorTask(device, state)
        peer_address = IPv4Address("10.0.0.1")
        # set initial state
        task.device_state.bgp_peer_admin_states = {peer_address: "running"}
        task.device_state.bgp_peer_oper_states = {peer_address: "established"}
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peer_oper_states[peer_address] != "established"
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, port=peer_address, event_class=BGPEvent)
        assert event
        assert event.admin_status == "running"
        assert event.operational_state == "down"
        assert event.remote_address == peer_address
        assert event.remote_as == 20
        assert event.peer_uptime == 1000000


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


class TestGetLocalAs:
    @pytest.mark.asyncio
    async def test_get_local_as_returns_correct_value_for_juniper(self, juniper_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(juniper_bgp_device, state)
        assert (await task._get_local_as(bgp_style="juniper")) == 10

    @pytest.mark.asyncio
    async def test_get_local_as_returns_correct_value_for_cisco(self, cisco_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(cisco_bgp_device, state)
        assert (await task._get_local_as(bgp_style="cisco")) == 10

    @pytest.mark.asyncio
    async def test_get_local_as_returns_correct_value_for_general(self, general_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(general_bgp_device, state)
        assert (await task._get_local_as(bgp_style="general")) == 10

    @pytest.mark.asyncio
    async def test_get_local_as_returns_none_for_non_existent_local_as(self, non_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(non_bgp_device, state)
        assert (await task._get_local_as(bgp_style="general")) is None


class TestFixupIPAddress:
    def test_can_parse_ipv4_starting_with_0x(self, general_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(general_bgp_device, state)
        encoded_address = "0x7f000001"
        decoded_address = task._fixup_ip_address(encoded_address)
        assert decoded_address == IPv4Address("127.0.0.1")

    def test_can_parse_ipv6_starting_with_0x(self, general_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(general_bgp_device, state)
        encoded_address = "0x13c7db1c4430c8266333aed0e6053a3b"
        decoded_address = task._fixup_ip_address(encoded_address)
        assert decoded_address == IPv6Address("13c7:db1c:4430:c826:6333:aed0:e605:3a3b")

    def test_can_parse_ipv4_in_string_format(self, general_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(general_bgp_device, state)
        string_address = "127.0.0.1"
        decoded_address = task._fixup_ip_address(string_address)
        assert decoded_address == IPv4Address(string_address)

    def test_can_parse_ipv6_in_string_format(self, general_bgp_device):
        state = ZinoState()
        task = BgpStateMonitorTask(general_bgp_device, state)
        string_address = "13c7:db1c:4430:c826:6333:aed0:e605:3a3b"
        decoded_address = task._fixup_ip_address(string_address)
        assert decoded_address == IPv6Address(string_address)


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
