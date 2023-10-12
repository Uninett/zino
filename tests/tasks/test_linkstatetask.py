import pytest

from zino.config.models import PollDevice
from zino.oid import OID
from zino.state import ZinoState
from zino.statemodels import Port
from zino.tasks.linkstatetask import (
    BaseInterfaceRow,
    CollectedInterfaceDataIsNotSaneError,
    LinkStateTask,
    MissingInterfaceTableData,
)


class TestLinkStateTask:
    @pytest.mark.asyncio
    async def test_run_should_not_create_event_if_links_are_up(self, linkstatetask_with_links_up):
        task = linkstatetask_with_links_up
        assert (await task.run()) is None
        assert len(task.state.events) == 0

    @pytest.mark.asyncio
    async def test_run_should_create_event_if_at_least_one_link_is_down(self, linkstatetask_with_one_link_down):
        task = linkstatetask_with_one_link_down
        assert (await task.run()) is None
        assert len(task.state.events) == 1

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


@pytest.fixture
def linkstatetask_with_links_up(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port, community="linksup")
    state = ZinoState()
    task = LinkStateTask(device, state)
    yield task


@pytest.fixture
def linkstatetask_with_one_link_down(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port, community="linksdown")
    state = ZinoState()
    task = LinkStateTask(device, state)
    yield task


@pytest.fixture
def task_with_dummy_device():
    device = PollDevice(name="test", address="127.0.0.1")
    state = ZinoState()
    task = LinkStateTask(device, state)
    yield task
