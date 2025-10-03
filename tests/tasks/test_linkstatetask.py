from datetime import timedelta
from unittest.mock import patch

import pytest

from zino.config.models import Configuration, PollDevice
from zino.oid import OID
from zino.state import ZinoState
from zino.statemodels import InterfaceState, Port, PortStateEvent
from zino.tasks.linkstatetask import (
    BaseInterfaceRow,
    CollectedInterfaceDataIsNotSaneError,
    LinkStateTask,
    MissingInterfaceTableData,
)
from zino.time import now


class TestLinkStateTask:
    async def test_run_should_not_create_event_if_links_are_up(self, linkstatetask_with_links_up):
        task = linkstatetask_with_links_up
        assert (await task.run()) is None
        assert len(task.state.events) == 0

    async def test_given_event_suppression_config_of_true_when_one_link_is_down_then_run_should_create_event(
        self, linkstatetask_with_one_link_down
    ):
        task = linkstatetask_with_one_link_down
        task.config.event.make_events_for_new_interfaces = True
        assert (await task.run()) is None
        assert len(task.state.events) == 1

    async def test_given_event_suppression_config_of_false_when_one_link_is_down_then_run_should_not_create_event(
        self, linkstatetask_with_one_link_down
    ):
        task = linkstatetask_with_one_link_down
        task.config.event.make_events_for_new_interfaces = False
        assert (await task.run()) is None
        assert len(task.state.events) == 0

    def test_when_patterns_are_empty_interface_should_not_be_ignored(self, task_with_dummy_device):
        data = BaseInterfaceRow(
            index=2, descr="GigabitEthernet1/2", alias="uplink", admin_status="up", oper_status="up", last_change=0
        )
        assert task_with_dummy_device._is_interface_watched(data)

    def test_when_interface_matches_watchpat_it_should_not_be_ignored(self, task_with_dummy_device):
        data = BaseInterfaceRow(
            index=2, descr="GigabitEthernet1/2", alias="uplink", admin_status="up", oper_status="up", last_change=0
        )
        task_with_dummy_device.device.watchpat = "Gigabit"
        assert task_with_dummy_device._is_interface_watched(data)

    def test_when_interface_matches_watchpat_not_at_the_beginning_it_should_not_be_ignored(
        self, task_with_dummy_device
    ):
        data = BaseInterfaceRow(
            index=2, descr="GigabitEthernet1/2", alias="uplink", admin_status="up", oper_status="up", last_change=0
        )
        task_with_dummy_device.device.watchpat = "1/2"
        assert task_with_dummy_device._is_interface_watched(data)

    def test_when_interface_doesnt_match_watchpat_it_should_be_ignored(self, task_with_dummy_device):
        data = BaseInterfaceRow(
            index=2, descr="GigabitEthernet1/2", alias="uplink", admin_status="up", oper_status="up", last_change=0
        )
        task_with_dummy_device.device.watchpat = "TenGiga"
        assert not task_with_dummy_device._is_interface_watched(data)

    def test_when_interface_matches_ignorepat_it_should_be_ignored(self, task_with_dummy_device):
        data = BaseInterfaceRow(
            index=2, descr="GigabitEthernet1/2", alias="uplink", admin_status="up", oper_status="up", last_change=0
        )
        task_with_dummy_device.device.ignorepat = ".*Ethernet"
        assert not task_with_dummy_device._is_interface_watched(data)

    def test_when_interface_matches_ignorepat_not_at_the_beginning_it_should_be_ignored(self, task_with_dummy_device):
        data = BaseInterfaceRow(
            index=2, descr="GigabitEthernet1/2", alias="uplink", admin_status="up", oper_status="up", last_change=0
        )
        task_with_dummy_device.device.ignorepat = "1/2"
        assert not task_with_dummy_device._is_interface_watched(data)

    def test_when_interface_state_is_missing_update_state_should_raise_exception(self, task_with_dummy_device):
        row = BaseInterfaceRow(index=42, descr="x", alias="x", admin_status="x", oper_status="x", last_change=0)
        port = Port(ifindex=42)
        empty_state_row = {}

        with pytest.raises(MissingInterfaceTableData):
            task_with_dummy_device._update_state(data=row, port=port, row=empty_state_row)

    def test_when_interface_data_is_empty_update_single_interface_should_raise_exception(self, task_with_dummy_device):
        with pytest.raises(CollectedInterfaceDataIsNotSaneError):
            task_with_dummy_device._update_single_interface({})

    def test_when_interface_data_is_empty_update_interfaces_should_keep_processing(self, task_with_dummy_device):
        assert (
            task_with_dummy_device._update_interfaces(
                {
                    OID(".1"): {},
                    OID(".2"): {},
                    OID(".3"): {},
                }
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_when_event_is_new_it_should_set_lasttrans(self, linkstatetask_with_one_link_down):
        task = linkstatetask_with_one_link_down
        task.config.event.make_events_for_new_interfaces = True
        await task.run()
        event = task.state.events.get(task.device.name, 2, PortStateEvent)
        assert event.lasttrans

    @pytest.mark.asyncio
    async def test_when_event_transitions_from_to_up_it_should_update_lasttrans(self, linkstatetask_with_links_up):
        task = linkstatetask_with_links_up
        initial_lasttrans = now() - timedelta(minutes=5)

        device = task.device_state
        device.ports.update({1: Port(ifindex=1, ifdescr="1", ifalias="from a famous", state=InterfaceState.DOWN)})

        event = task.state.events.create_event(task.device.name, 1, PortStateEvent)
        event.ifindex = 1
        event.portstate = InterfaceState.DOWN
        event.lasttrans = initial_lasttrans
        task.state.events.commit(event)

        assert (await task.run()) is None
        updated_event = task.state.events[event.id]
        assert updated_event.portstate == InterfaceState.UP
        assert updated_event.lasttrans > initial_lasttrans

    @pytest.mark.asyncio
    async def test_when_event_transitions_from_down_to_admindown_it_should_update_lasttrans(
        self, linkstatetask_with_admin_down
    ):
        task = linkstatetask_with_admin_down
        initial_lasttrans = now() - timedelta(minutes=5)

        device = task.device_state
        device.ports.update({1: Port(ifindex=1, ifdescr="1", ifalias="from a famous", state=InterfaceState.DOWN)})

        event = task.state.events.create_event(task.device.name, 1, PortStateEvent)
        event.ifindex = 1
        event.portstate = InterfaceState.DOWN
        event.lasttrans = initial_lasttrans
        task.state.events.commit(event)

        assert (await task.run()) is None
        updated_event = task.state.events[event.id]
        assert updated_event.portstate == InterfaceState.ADMIN_DOWN
        assert updated_event.lasttrans > initial_lasttrans

    @pytest.mark.asyncio
    async def test_when_event_transitions_from_down_to_up_it_should_update_ac_down(self, linkstatetask_with_links_up):
        task = linkstatetask_with_links_up
        initial_lasttrans = now() - timedelta(minutes=5)
        initial_ac_down = timedelta(0)

        device = task.device_state
        device.ports.update({1: Port(ifindex=1, ifdescr="1", ifalias="from a famous", state=InterfaceState.DOWN)})

        event = task.state.events.create_event(task.device.name, 1, PortStateEvent)
        event.ifindex = 1
        event.portstate = InterfaceState.DOWN
        event.ac_down = initial_ac_down
        event.lasttrans = initial_lasttrans
        task.state.events.commit(event)

        assert (await task.run()) is None
        updated_event = task.state.events[event.id]
        assert updated_event.portstate == InterfaceState.UP
        assert updated_event.ac_down > initial_ac_down

    @pytest.mark.asyncio
    async def test_when_event_transitions_from_down_to_admindown_it_should_update_ac_down(
        self, linkstatetask_with_admin_down
    ):
        task = linkstatetask_with_admin_down
        initial_lasttrans = now() - timedelta(minutes=5)
        initial_ac_down = timedelta(0)

        device = task.device_state
        device.ports.update({1: Port(ifindex=1, ifdescr="1", ifalias="alias", state=InterfaceState.DOWN)})

        event = task.state.events.create_event(task.device.name, 1, PortStateEvent)
        event.ifindex = 1
        event.portstate = InterfaceState.DOWN
        event.ac_down = initial_ac_down
        event.lasttrans = initial_lasttrans
        task.state.events.commit(event)

        assert (await task.run()) is None
        updated_event = task.state.events[event.id]
        assert updated_event.portstate == InterfaceState.ADMIN_DOWN
        assert updated_event.ac_down > initial_ac_down


class TestBaseInterfaceRow:
    def test_when_index_is_missing_is_sane_should_return_false(self):
        row = BaseInterfaceRow(index=None, descr="x", alias="x", admin_status="x", oper_status="x", last_change=0)
        assert not row.is_sane()

    def test_when_descr_is_missing_is_sane_should_return_false(self):
        row = BaseInterfaceRow(index=42, descr=None, alias="x", admin_status="x", oper_status="x", last_change=0)
        assert not row.is_sane()

    def test_when_descr_and_index_are_present_is_sane_should_return_true(self):
        row = BaseInterfaceRow(index=42, descr="x", alias="x", admin_status="x", oper_status="x", last_change=0)
        assert row.is_sane()

    async def test_poll_single_interface_should_update_state(self, linkstatetask_with_one_link_down):
        target_index = 2
        await linkstatetask_with_one_link_down.poll_single_interface(target_index)
        device_state = linkstatetask_with_one_link_down.state.devices.get(linkstatetask_with_one_link_down.device.name)

        assert target_index in device_state.ports, f"no state for port {target_index} was stored"
        port = device_state.ports[target_index]
        assert port.state == InterfaceState.DOWN
        assert port.ifdescr == "2"
        assert port.ifalias == "from a famous"

    async def test_when_ifindex_is_1_poll_single_interface_should_not_crash(self, linkstatetask_with_one_link_down):
        """Regression test.  poll_single_interface constructs a GET-NEXT request by asking for the set of next values
        after ifindex-1 - but 0 indexes are illegal when encoding OIDs into tables.
        """
        target_index = 1
        assert await linkstatetask_with_one_link_down.poll_single_interface(target_index) is None

    async def test_when_timeout_occurs_poll_single_interface_should_not_crash(self, linkstatetask_with_one_link_down):
        with patch.object(linkstatetask_with_one_link_down.snmp, "getnext2") as mock_getnext2:
            mock_getnext2.side_effect = TimeoutError
            assert await linkstatetask_with_one_link_down.poll_single_interface(42) is None


@pytest.fixture
def linkstatetask_with_links_up(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port, community="linksup")
    state = ZinoState()
    task = LinkStateTask(device, state, Configuration())
    yield task


@pytest.fixture
def linkstatetask_with_one_link_down(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port, community="linksdown")
    state = ZinoState()
    task = LinkStateTask(device, state, Configuration())
    yield task


@pytest.fixture
def linkstatetask_with_admin_down(snmpsim, snmp_test_port):
    device = PollDevice(
        name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port, community="linksadmindown"
    )
    state = ZinoState()
    task = LinkStateTask(device, state, Configuration())
    yield task


@pytest.fixture
def task_with_dummy_device():
    device = PollDevice(name="test", address="127.0.0.1")
    state = ZinoState()
    task = LinkStateTask(device, state, Configuration())
    yield task
