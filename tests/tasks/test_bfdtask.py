from ipaddress import IPv4Address

import pytest

from zino.config.models import PollDevice
from zino.oid import OID
from zino.state import ZinoState
from zino.statemodels import BFDEvent, BFDSessState, BFDState, Port
from zino.tasks.bfdtask import BFDTask


class TestJuniper:
    @pytest.mark.parametrize("task", ["juniper-bfd-up"], indirect=True)
    def test_parse_row_creates_correct_bfd_state(self, task, bfd_state):
        state = task._parse_row(
            OID(f".{bfd_state.session_index}"),
            "up",
            bfd_state.session_discr,
            "0x7f000001",
        )
        assert state == bfd_state

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", ["juniper-bfd-up"], indirect=True)
    async def test_poll_juniper_returns_correct_ifdescr_to_state_mapping(self, task, bfd_state, device_port):
        result = await task._poll_juniper()
        assert device_port.ifdescr in result
        state = result.get(device_port.ifdescr)
        assert state == bfd_state


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ["juniper-bfd-up", "cisco-bfd-up"], indirect=True)
async def test_task_updates_state_correctly(task, device_port, bfd_state):
    assert not device_port.bfd_state
    await task.run()
    assert device_port.bfd_state == bfd_state


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ["juniper-bfd-down", "cisco-bfd-down"], indirect=True)
async def test_event_should_be_made_the_first_time_a_port_is_polled_if_state_is_not_up(task, device_port):
    assert not device_port.bfd_state
    await task.run()
    assert device_port.bfd_state
    event = task.state.events.get(
        device_name=task.device.name,
        subindex=device_port.ifindex,
        event_class=BFDEvent,
    )
    assert event


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ["juniper-bfd-up", "cisco-bfd-up"], indirect=True)
async def test_event_should_not_be_made_the_first_time_a_port_is_polled_if_state_is_up(task, device_port):
    assert not device_port.bfd_state
    await task.run()
    assert device_port.bfd_state
    event = task.state.events.get(
        device_name=task.device.name,
        subindex=device_port.ifindex,
        event_class=BFDEvent,
    )
    assert not event


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ["juniper-bfd-up", "cisco-bfd-up"], indirect=True)
async def test_state_changing_should_create_event(task, device_port, bfd_state):
    down_state = BFDState(session_state=BFDSessState.DOWN, session_index=bfd_state.session_index)
    device_port.bfd_state = down_state
    await task.run()
    assert device_port.bfd_state != down_state
    event = task.state.events.get(device_name=task.device.name, subindex=device_port.ifindex, event_class=BFDEvent)
    assert event


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ["juniper-bfd-up", "cisco-bfd-up"], indirect=True)
async def test_state_not_changing_should_not_create_event(task, device_port, bfd_state):
    device_port.bfd_state = bfd_state
    await task.run()
    assert device_port.bfd_state == bfd_state
    event = task.state.events.get(device_name=task.device.name, subindex=device_port.ifindex, event_class=BFDEvent)
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


@pytest.fixture(scope="function")
def task(request, snmpsim, snmp_test_port, device_port):
    device = PollDevice(
        name="buick.lab.example.org",
        address="127.0.0.1",
        port=snmp_test_port,
        community=request.param,
    )
    state = ZinoState()
    device_state = state.devices.get(device_name=device.name)
    if "cisco" in request.param:
        device_state.enterprise_id = 9
    elif "juniper" in request.param:
        device_state.enterprise_id = 2636
    # this effectively makes the device_port fixture a shortcut for accessing
    # the port that will change bfd_state when the task is run
    device_state.ports[device_port.ifindex] = device_port
    task = BFDTask(device, state)
    yield task
