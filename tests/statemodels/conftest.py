import pytest

from zino.state import ZinoState
from zino.statemodels import DeviceState, Port, PortStateEvent, ReachabilityEvent


@pytest.fixture
def state() -> ZinoState:
    return ZinoState()


@pytest.fixture
def port() -> Port:
    return Port(ifindex=1, ifdescr="port")


@pytest.fixture
def device(state, port) -> DeviceState:
    device = state.devices.get("device")
    device.ports[port.ifindex] = port
    return device


@pytest.fixture
def reachability_event(state, device) -> ReachabilityEvent:
    event = state.events.create_event(device.name, None, ReachabilityEvent)
    state.events.commit(event)
    return state.events.get(event.router, event.subindex, ReachabilityEvent)


@pytest.fixture
def portstate_event(state, device, port) -> PortStateEvent:
    event = state.events.create_event(device.name, port.ifindex, PortStateEvent)
    event.ifindex = port.ifindex
    state.events.commit(event)
    return state.events.get(event.router, event.subindex, PortStateEvent)
