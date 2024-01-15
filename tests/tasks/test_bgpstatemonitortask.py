from ipaddress import IPv4Address, IPv6Address

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
    task = BGPStateMonitorTask(device, state)
    if BGPStyle.CISCO in request.param:
        task.device_state.bgp_style = BGPStyle.CISCO
    elif BGPStyle.JUNIPER in request.param:
        task.device_state.bgp_style = BGPStyle.JUNIPER
    elif BGPStyle.GENERAL in request.param:
        task.device_state.bgp_style = BGPStyle.GENERAL
    yield task
