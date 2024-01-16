import ipaddress
from ipaddress import IPv4Address

import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.tasks.addrs import AddressMapTask, validate_ipaddr


class TestAddressMapTask:
    @pytest.mark.asyncio
    async def test_it_should_run_without_error_on_reachable_device(self, address_task_with_dummy_device):
        result = await address_task_with_dummy_device.run()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_addrs_should_find_addresses(self, address_task_with_dummy_device):
        result = await address_task_with_dummy_device._get_addrs()
        assert result == {
            IPv4Address("8.8.8.8"),
            IPv4Address("10.0.0.4"),
            IPv4Address("10.129.0.10"),
            IPv4Address("127.0.0.1"),
            IPv4Address("128.0.0.1"),
            IPv4Address("128.0.0.4"),
        }

    @pytest.mark.asyncio
    async def test_when_address_is_removed_it_should_update_the_state_accordingly(self, address_task_with_dummy_device):
        dead_address = IPv4Address("192.0.168.42")

        device = address_task_with_dummy_device.device_state
        state = address_task_with_dummy_device.state
        state.addresses[dead_address] = device.name

        device.addresses = {dead_address}
        await address_task_with_dummy_device.run()

        assert dead_address not in device.addresses
        assert dead_address not in state.addresses

    @pytest.mark.asyncio
    async def test_when_address_is_taken_from_other_device_it_should_update_the_state_accordingly(
        self, address_task_with_dummy_device
    ):
        old_address = IPv4Address("8.8.8.8")
        state = address_task_with_dummy_device.state
        state.addresses[old_address] = "some-other-device"

        await address_task_with_dummy_device.run()

        assert state.addresses[old_address] == address_task_with_dummy_device.device.name


@pytest.mark.parametrize(
    "address,expected", [("128.0.0.1", True), ("8.8.8.8", False), ("192.168.42.42", True), ("172.16.0.1", True)]
)
def test_is_ignored(address, expected):
    assert AddressMapTask.is_ignored(ipaddress.ip_address(address)) == expected


class TestValidateIpAddr:
    def test_when_input_is_valid_ipv4_it_should_return_an_ipv4address(self):
        assert validate_ipaddr("192.168.0.1") == IPv4Address("192.168.0.1")

    def test_when_input_is_valid_ipv6_it_should_return_an_ipv6address(self):
        assert validate_ipaddr("fe80::1234") == ipaddress.IPv6Address("fe80::1234")

    def test_when_input_is_invalid_ip_it_should_return_none(self):
        assert validate_ipaddr("f--320w54r-23045") is None


@pytest.fixture()
def address_task_with_dummy_device(snmpsim, snmp_test_port) -> AddressMapTask:
    device = PollDevice(
        name="buick.lab.example.org",
        address="127.0.0.1",
        port=snmp_test_port,
        community="ipadentaddr",
    )
    state = ZinoState()
    task = AddressMapTask(device, state)
    yield task
