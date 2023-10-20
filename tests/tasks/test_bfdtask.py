import ipaddress
from ipaddress import IPv4Address

import pytest

from zino.config.models import PollDevice
from zino.oid import OID
from zino.state import ZinoState
from zino.statemodels import BFDEvent, BFDSessState, BFDState, Port
from zino.tasks.bfdtask import BFDTask


class TestParseAddress:
    def test_converts_bytes_to_correct_ipv6_address(self):
        parsed_address = BFDTask._convert_address(
            b"\x00\x00\x00\x00\x00\x00\x00\x00\00\x00\x00\x00\x00\x00\x00\x01",
            "ipv6",
        )
        assert parsed_address == ipaddress.IPv6Address("::1")

    def test_converts_bytes_to_correct_ipv4_address(self):
        parsed_address = BFDTask._convert_address(b"\x7f\x00\x00\x01", "ipv4")
        assert parsed_address == ipaddress.IPv4Address("127.0.0.1")

    def test_fails_if_parsing_ipv4_as_ipv6(self):
        with pytest.raises(ipaddress.AddressValueError):
            BFDTask._convert_address(b"\x7f\x00\x00\x01", "ipv6")

    def test_fails_if_parsing_ipv6_as_ipv4(self):
        with pytest.raises(ipaddress.AddressValueError):
            BFDTask._convert_address(
                b"\x00\x00\x00\x00\x00\x00\x00\x00\00\x00\x00\x00\x00\x00\x00\x01",
                "ipv4",
            )

    def test_fails_if_address_type_is_invalid(self):
        with pytest.raises(ValueError):
            BFDTask._convert_address("\x7f\x00\x00\x01", "invalid")


class TestJuniper:
    def test_parse_juniper_rows_creates_correct_bfd_state(self, bfd_task_juniper, bfd_state, device_port):
        fake_sparsewalk_response = {
            OID(f".{bfd_state.session_index}"): {
                "jnxBfdSessIntfName": device_port.ifdescr,
                "bfdSessState": "up",
                "bfdSessDiscriminator": bfd_state.session_index,
                "bfdSessAddr": "0x7f000001",
                "bfdSessAddrType": "ipv4",
            },
        }
        parsed_rows = bfd_task_juniper._parse_juniper_rows(fake_sparsewalk_response)
        state = parsed_rows.get(device_port.ifdescr)
        assert state == bfd_state

    @pytest.mark.asyncio
    async def test_poll_juniper_returns_correct_ifdescr_to_state_mapping(
        self, bfd_task_juniper, bfd_state, device_port
    ):
        result = await bfd_task_juniper._poll_juniper()
        assert device_port.ifdescr in result
        state = result.get(device_port.ifdescr)
        assert state == bfd_state

    @pytest.mark.asyncio
    async def test_task_updates_state_correctly(self, bfd_task_juniper, device_port, bfd_state):
        assert not device_port.bfd_state
        await bfd_task_juniper.run()
        assert device_port.bfd_state == bfd_state

    @pytest.mark.asyncio
    async def test_event_should_not_be_made_the_first_time_a_port_is_polled(self, bfd_task_juniper, device_port):
        assert not device_port.bfd_state
        await bfd_task_juniper.run()
        assert device_port.bfd_state
        event = bfd_task_juniper.state.events.get(
            device_name=bfd_task_juniper.device.name,
            port=device_port.ifindex,
            event_class=BFDEvent,
        )
        assert not event

    @pytest.mark.asyncio
    async def test_state_changing_should_create_event(self, bfd_task_juniper, device_port, bfd_state):
        down_state = BFDState(session_state=BFDSessState.DOWN, session_index=bfd_state.session_index)
        device_port.bfd_state = down_state
        await bfd_task_juniper.run()
        assert device_port.bfd_state != down_state
        event = bfd_task_juniper.state.events.get(
            device_name=bfd_task_juniper.device.name, port=device_port.ifindex, event_class=BFDEvent
        )
        assert event

    @pytest.mark.asyncio
    async def test_state_not_changing_should_not_create_event(self, bfd_task_juniper, device_port, bfd_state):
        device_port.bfd_state = bfd_state
        await bfd_task_juniper.run()
        assert device_port.bfd_state == bfd_state
        event = bfd_task_juniper.state.events.get(
            device_name=bfd_task_juniper.device.name, port=device_port.ifindex, event_class=BFDEvent
        )
        assert not event


@pytest.fixture()
def device_port():
    """Port related to the BFD state at the simulated device"""
    yield Port(ifindex=1, ifdescr="xe-1/2/0.0")


@pytest.fixture()
def bfd_state():
    """Represents the BFD state at the simulated device"""
    yield BFDState(
        session_state=BFDSessState.UP,
        session_index=4524,
        session_discr=4524,
        session_addr=IPv4Address("127.0.0.1"),
    )


@pytest.fixture()
def bfd_task_juniper(snmpsim, snmp_test_port, device_port):
    device = PollDevice(
        name="buick.lab.example.org",
        address="127.0.0.1",
        port=snmp_test_port,
        community="juniper-bfd-up",
    )
    state = ZinoState()
    device_state = state.devices.get(device_name=device.name)
    device_state.enterprise_id = 2636

    # this effectively makes the device_port fixture a shortcut for accessing
    # the port that will change bfd_state when the task is run
    device_state.ports[device_port.ifindex] = device_port
    task = BFDTask(device, state)
    yield task
