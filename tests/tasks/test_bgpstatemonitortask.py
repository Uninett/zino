import logging

import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
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
