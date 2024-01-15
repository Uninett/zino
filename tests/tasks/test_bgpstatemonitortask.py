import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.statemodels import BGPStyle
from zino.tasks.bgpstatemonitortask import BGPStateMonitorTask


class TestGetBGPStyle:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["juniper-bgp"], indirect=True)
    async def test_get_bgp_style_returns_correct_style_for_juniper(self, task):
        assert (await task._get_bgp_style()) == BGPStyle.JUNIPER

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["cisco-bgp"], indirect=True)
    async def test_get_bgp_style_returns_correct_style_for_cisco(self, task):
        assert (await task._get_bgp_style()) == BGPStyle.CISCO

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["general-bgp"], indirect=True)
    async def test_get_bgp_style_returns_correct_style_for_general(self, task):
        assert (await task._get_bgp_style()) == BGPStyle.GENERAL

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["public"], indirect=True)
    async def test_get_bgp_style_returns_correct_style_for_non_bgp_task(self, task):
        assert (await task._get_bgp_style()) is None


class TestGetLocalAs:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["juniper-bgp"], indirect=True)
    async def test_get_local_as_returns_correct_value_for_juniper(self, task):
        assert (await task._get_local_as(bgp_style=BGPStyle.JUNIPER)) == 10

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["cisco-bgp"], indirect=True)
    async def test_get_local_as_returns_correct_value_for_cisco(self, task):
        assert (await task._get_local_as(bgp_style=BGPStyle.CISCO)) == 10

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["general-bgp"], indirect=True)
    async def test_get_local_as_returns_correct_value_for_general(self, task):
        assert (await task._get_local_as(bgp_style=BGPStyle.GENERAL)) == 10

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["public"], indirect=True)
    async def test_get_local_as_returns_none_for_non_existent_local_as(self, task):
        assert (await task._get_local_as(bgp_style=BGPStyle.GENERAL)) is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["public"], indirect=True)
    async def test_get_local_as_returns_none_for_non_existent_local_as_with_juniper_bgp_style(self, task):
        assert (await task._get_local_as(bgp_style=BGPStyle.JUNIPER)) is None


@pytest.fixture
def task(request, snmpsim, snmp_test_port):
    device = PollDevice(
        name="buick.lab.example.org",
        address="127.0.0.1",
        community=request.param,
        port=snmp_test_port,
    )
    state = ZinoState()
    task = BGPStateMonitorTask(device, state)
    if BGPStyle.CISCO in request.param:
        task.device_state.bgp_style = BGPStyle.CISCO
    elif BGPStyle.JUNIPER in request.param:
        task.device_state.bgp_style = BGPStyle.JUNIPER
    elif BGPStyle.GENERAL in request.param:
        task.device_state.bgp_style = BGPStyle.GENERAL
    yield task
