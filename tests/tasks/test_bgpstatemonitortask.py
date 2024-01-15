import logging
from ipaddress import IPv4Address, IPv6Address

import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.statemodels import BGPEvent
from zino.tasks.bgpstatemonitortask import BgpStateMonitorTask


class TestBgpStateMonitorTask:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["public", "juniper-bgp", "cisco-bgp", "general-bgp"], indirect=True)
    async def test_task_runs_without_errors(self, task):
        assert (await task.run()) is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["missing-info-bgp"], indirect=True)
    async def test_task_logs_missing_information(self, task, caplog):
        """Tests that the BGP state monitor task logs if necessary information for a BGP device is missing"""
        with caplog.at_level(logging.INFO):
            await task.run()

        assert f"router {task.device.name} misses BGP variables" in caplog.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["general-bgp-external-reset", "cisco-bgp-external-reset"], indirect=True)
    async def test_external_reset_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a device has been reset"""
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
    @pytest.mark.parametrize("task", ["juniper-bgp-external-reset"], indirect=True)
    async def test_external_reset_juniper_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a juniper device has been reset"""
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
    @pytest.mark.parametrize("task", ["general-bgp-external-reset", "cisco-bgp-external-reset"], indirect=True)
    async def test_session_up_updates_event(self, task):
        """Tests that the oper down event should be updated if a BGP connection to a device reports that their
        oper_state has changed back to established
        """
        peer_address = IPv4Address("10.0.0.1")
        # create admin down event
        event = task.state.events.get_or_create_event(
            device_name=task.device.name, port=peer_address, event_class=BGPEvent
        )
        event.operational_state = "down"
        event.admin_status = "stop"
        event.remote_address = peer_address
        event.remote_as = 20
        event.peer_uptime = 0
        task.state.events.commit(event=event)

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
    @pytest.mark.parametrize("task", ["juniper-bgp-external-reset"], indirect=True)
    async def test_session_up_juniper_updates_event(self, task):
        """Tests that the oper down event should be updated if a BGP connection to a juniper device reports that their
        oper_state has changed back to established
        """
        peer_address = IPv4Address("10.0.0.1")
        # create admin down event
        event = task.state.events.get_or_create_event(
            device_name=task.device.name, port=peer_address, event_class=BGPEvent
        )
        event.operational_state = "down"
        event.admin_status = "halted"
        event.remote_address = peer_address
        event.remote_as = 20
        event.peer_uptime = 0
        task.state.events.commit(event=event)

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
    @pytest.mark.parametrize("task", ["general-bgp-admin-down", "cisco-bgp-admin-down"], indirect=True)
    async def test_admin_down_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a device reports that their admin_state has changed
        from start to stop
        """
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
    @pytest.mark.parametrize("task", ["juniper-bgp-admin-down"], indirect=True)
    async def test_admin_down_juniper_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a juniper device reports that their admin_state has
        changed from running to halted
        """
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
    @pytest.mark.parametrize("task", ["general-bgp-admin-up", "cisco-bgp-admin-up"], indirect=True)
    async def test_admin_up_general_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a device reports that their admin_state has changed
        from stop to start
        """
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
    @pytest.mark.parametrize("task", ["juniper-bgp-admin-up"], indirect=True)
    async def test_admin_up_juniper_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a juniper device reports that their admin_state has
        changed from halted to running
        """
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
    @pytest.mark.parametrize("task", ["general-bgp-oper-down", "cisco-bgp-oper-down"], indirect=True)
    async def test_oper_down_general_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a device reports that their oper_state has changed
        from established to something else
        """
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
    @pytest.mark.parametrize("task", ["juniper-bgp-oper-down"], indirect=True)
    async def test_oper_down_juniper_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a juniper device reports that their oper_state has
        changed from established to something else
        """
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
    @pytest.mark.parametrize("task", ["juniper-bgp"], indirect=True)
    async def test_get_bgp_type_returns_correct_type_for_juniper(self, task):
        assert (await task._get_bgp_style()) == "juniper"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["cisco-bgp"], indirect=True)
    async def test_get_bgp_type_returns_correct_type_for_cisco(self, task):
        assert (await task._get_bgp_style()) == "cisco"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["general-bgp"], indirect=True)
    async def test_get_bgp_type_returns_correct_type_for_general(self, task):
        assert (await task._get_bgp_style()) == "general"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["public"], indirect=True)
    async def test_get_bgp_type_returns_correct_type_for_non_bgp_task(self, task):
        assert (await task._get_bgp_style()) is None


class TestGetLocalAs:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["juniper-bgp"], indirect=True)
    async def test_get_local_as_returns_correct_value_for_juniper(self, task):
        assert (await task._get_local_as(bgp_style="juniper")) == 10

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["cisco-bgp"], indirect=True)
    async def test_get_local_as_returns_correct_value_for_cisco(self, task):
        assert (await task._get_local_as(bgp_style="cisco")) == 10

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["general-bgp"], indirect=True)
    async def test_get_local_as_returns_correct_value_for_general(self, task):
        assert (await task._get_local_as(bgp_style="general")) == 10

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["public"], indirect=True)
    async def test_get_local_as_returns_none_for_non_existent_local_as(self, task):
        assert (await task._get_local_as(bgp_style="general")) is None


class TestFixupIPAddress:
    @pytest.mark.parametrize("task", ["general-bgp"], indirect=True)
    def test_can_parse_ipv4_starting_with_0x(self, task):
        encoded_address = "0x7f000001"
        decoded_address = task._fixup_ip_address(encoded_address)
        assert decoded_address == IPv4Address("127.0.0.1")

    @pytest.mark.parametrize("task", ["general-bgp"], indirect=True)
    def test_can_parse_ipv6_starting_with_0x(self, task):
        encoded_address = "0x13c7db1c4430c8266333aed0e6053a3b"
        decoded_address = task._fixup_ip_address(encoded_address)
        assert decoded_address == IPv6Address("13c7:db1c:4430:c826:6333:aed0:e605:3a3b")

    @pytest.mark.parametrize("task", ["general-bgp"], indirect=True)
    def test_can_parse_ipv4_in_string_format(self, task):
        string_address = "127.0.0.1"
        decoded_address = task._fixup_ip_address(string_address)
        assert decoded_address == IPv4Address(string_address)

    @pytest.mark.parametrize("task", ["general-bgp"], indirect=True)
    def test_can_parse_ipv6_in_string_format(self, task):
        string_address = "13c7:db1c:4430:c826:6333:aed0:e605:3a3b"
        decoded_address = task._fixup_ip_address(string_address)
        assert decoded_address == IPv6Address(string_address)


@pytest.fixture
def task(request, snmpsim, snmp_test_port):
    device = PollDevice(
        name="buick.lab.example.org",
        address="127.0.0.1",
        community=request.param,
        port=snmp_test_port,
    )
    state = ZinoState()
    task = BgpStateMonitorTask(device, state)
    yield task
