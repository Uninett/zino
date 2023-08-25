import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.tasks.linkstatetask import BaseInterfaceRow, LinkStateTask


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
