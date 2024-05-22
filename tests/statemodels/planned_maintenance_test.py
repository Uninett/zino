import datetime

import pytest

from zino.state import ZinoState
from zino.statemodels import (
    DeviceState,
    EventState,
    PlannedMaintenance,
    Port,
    PortStateEvent,
    ReachabilityEvent,
)


class TestPlannedMaintenanceMatchesPortstate:
    @pytest.mark.parametrize("regexp_pm", ["portstate"], indirect=True)
    def test_regexp_type_should_return_true_for_ifdescr_matching_regex(self, regexp_pm, device, port):
        assert regexp_pm.matches_portstate(device, port)

    @pytest.mark.parametrize("regexp_pm", ["portstate"], indirect=True)
    def test_regexp_type_should_return_false_for_ifdescr_not_matching_regex(self, regexp_pm, device, port):
        port.ifdescr = "wrongport"
        assert not regexp_pm.matches_portstate(device, port)

    def test_intf_regexp_type_should_return_true_for_ifdescr_and_device_name_matching_regex(
        self, intf_regex_pm, device, port
    ):
        assert intf_regex_pm.matches_portstate(device, port)

    def test_intf_regexp_type_should_return_false_for_ifdescr_not_matching_regex(self, intf_regex_pm, device, port):
        port.ifdescr = "wrongport"
        assert not intf_regex_pm.matches_portstate(device, port)

    def test_intf_regexp_type_should_return_false_for_device_name_not_matching_regex(self, intf_regex_pm, device, port):
        device.name = "wrongdevice"
        assert not intf_regex_pm.matches_portstate(device, port)

    @pytest.mark.parametrize("str_pm", ["portstate"], indirect=True)
    def test_str_type_should_return_true_for_ifdescr_matching_str(self, str_pm, device, port):
        assert str_pm.matches_portstate(device, port)

    @pytest.mark.parametrize("str_pm", ["portstate"], indirect=True)
    def test_str_type_should_return_false_for_ifdescr_not_matching_str(self, str_pm, device, port):
        port.ifdescr = "wrongport"
        assert not str_pm.matches_portstate(device, port)

    @pytest.mark.parametrize("str_pm", ["device"], indirect=True)
    def test_should_return_false_if_pm_type_is_not_portstate(self, str_pm, device, port):
        assert not str_pm.matches_portstate(device, port)


class TestPlannedMaintenanceMatchesDevice:
    def test_exact_type_should_return_true_for_exact_device_name(self, exact_pm, device):
        assert exact_pm.matches_device(device)

    def test_exact_type_should_return_false_for_nonexact_device_name(self, exact_pm, device):
        device.name = "wrongdevice"
        assert not exact_pm.matches_device(device)

    @pytest.mark.parametrize("regexp_pm", ["device"], indirect=True)
    def test_regexp_type_should_return_true_for_device_name_matching_regex(self, regexp_pm, device):
        assert regexp_pm.matches_device(device)

    @pytest.mark.parametrize("regexp_pm", ["device"], indirect=True)
    def test_regexp_type_should_return_false_for_device_name_not_matching_regex(self, regexp_pm, device):
        device.name = "wrongdevice"
        assert not regexp_pm.matches_device(device)

    @pytest.mark.parametrize("str_pm", ["device"], indirect=True)
    def test_str_type_should_return_true_for_device_name_matching_str(self, str_pm, device):
        assert str_pm.matches_device(device)

    @pytest.mark.parametrize("str_pm", ["device"], indirect=True)
    def test_str_type_should_return_false_for_device_name_not_matching_str(self, str_pm, device):
        device.name = "wrongdevice"
        assert not str_pm.matches_device(device)

    @pytest.mark.parametrize("str_pm", ["portstate"], indirect=True)
    def test_should_return_false_if_pm_type_is_not_device(self, str_pm, device):
        assert not str_pm.matches_device(device)


class TestPlannedMaintenanceMatchesEventWithDeviceType:
    def test_exact_type_should_return_true_for_event_with_matching_router_name(self, exact_pm, reachable_event, state):
        assert exact_pm.matches_event(reachable_event, state)

    def test_exact_type_should_return_false_for_event_with_non_matching_router_name(
        self, exact_pm, mismatch_reachable_event, state
    ):
        assert not exact_pm.matches_event(mismatch_reachable_event, state)

    @pytest.mark.parametrize("regexp_pm", ["device"], indirect=True)
    def test_regexp_type_should_return_true_for_event_with_matching_router_name(
        self, regexp_pm, reachable_event, state
    ):
        assert regexp_pm.matches_event(reachable_event, state)

    @pytest.mark.parametrize("regexp_pm", ["device"], indirect=True)
    def test_regexp_type_should_return_false_for_event_with_non_matching_router_name(
        self, regexp_pm, mismatch_reachable_event, state
    ):
        assert not regexp_pm.matches_event(mismatch_reachable_event, state)

    @pytest.mark.parametrize("str_pm", ["device"], indirect=True)
    def test_str_type_should_return_true_for_event_with_matching_router_name(self, str_pm, reachable_event, state):
        assert str_pm.matches_event(reachable_event, state)

    @pytest.mark.parametrize("str_pm", ["device"], indirect=True)
    def test_str_type_should_return_false_for_event_with_non_matching_router_name(
        self, str_pm, mismatch_reachable_event, state
    ):
        assert not str_pm.matches_event(mismatch_reachable_event, state)


class TestPlannedMaintenanceMatchesEventWithPortstateType:
    def test_intf_regex_pm_type_should_return_true_for_event_with_matching_ifdescr_and_router_name(
        self, intf_regex_pm, portstate_event, state
    ):
        assert intf_regex_pm.matches_event(portstate_event, state)

    def test_intf_regex_pm_type_should_return_false_for_event_with_non_matching_ifdescr(
        self, intf_regex_pm, portstate_event_wrong_ifdescr, state
    ):
        assert not intf_regex_pm.matches_event(portstate_event_wrong_ifdescr, state)

    def test_intf_regex_pm_type_should_return_true_for_event_with_non_matching_router_name(
        self, intf_regex_pm, portstate_event_wrong_router, state
    ):
        assert not intf_regex_pm.matches_event(portstate_event_wrong_router, state)

    @pytest.mark.parametrize("regexp_pm", ["portstate"], indirect=True)
    def test_regexp_type_should_return_true_for_event_with_matching_ifdescr(self, regexp_pm, portstate_event, state):
        assert regexp_pm.matches_event(portstate_event, state)

    @pytest.mark.parametrize("regexp_pm", ["portstate"], indirect=True)
    def test_regexp_type_should_return_false_for_event_with_non_matching_ifdescr(
        self, regexp_pm, portstate_event_wrong_ifdescr, state
    ):
        assert not regexp_pm.matches_event(portstate_event_wrong_ifdescr, state)

    @pytest.mark.parametrize("str_pm", ["portstate"], indirect=True)
    def test_str_type_should_return_true_for_event_with_matching_ifdescr(self, str_pm, portstate_event, state):
        assert str_pm.matches_event(portstate_event, state)

    @pytest.mark.parametrize("str_pm", ["portstate"], indirect=True)
    def test_str_type_should_return_false_for_event_with_non_matching_ifdescr(
        self, str_pm, portstate_event_wrong_ifdescr, state
    ):
        assert not str_pm.matches_event(portstate_event_wrong_ifdescr, state)


@pytest.fixture
def state() -> ZinoState:
    return ZinoState()


@pytest.fixture
def device(state, port, wrong_port) -> DeviceState:
    device = state.devices.get("device")
    device.ports[port.ifindex] = port
    device.ports[wrong_port.ifindex] = wrong_port
    return device


@pytest.fixture
def port() -> Port:
    return Port(ifindex=1, ifdescr="port")


@pytest.fixture
def reachable_event(device) -> ReachabilityEvent:
    return ReachabilityEvent(id=1, router=device.name, state=EventState.OPEN)


@pytest.fixture
def portstate_event(device, port) -> ReachabilityEvent:
    return PortStateEvent(id=3, router=device.name, state=EventState.OPEN, ifindex=port.ifindex)


@pytest.fixture
def wrong_device(state, port, wrong_port) -> DeviceState:
    device = state.devices.get("wrongdevice")
    device.ports[port.ifindex] = port
    device.ports[wrong_port.ifindex] = wrong_port
    return device


@pytest.fixture
def wrong_port() -> Port:
    return Port(ifindex=2, ifdescr="wrongport")


@pytest.fixture
def mismatch_reachable_event(wrong_device) -> ReachabilityEvent:
    return ReachabilityEvent(id=2, router=wrong_device.name, state=EventState.OPEN)


@pytest.fixture
def portstate_event_wrong_ifdescr(device, wrong_port) -> ReachabilityEvent:
    return PortStateEvent(id=4, router=device.name, state=EventState.OPEN, ifindex=wrong_port.ifindex)


@pytest.fixture
def portstate_event_wrong_router(wrong_device, port) -> ReachabilityEvent:
    return PortStateEvent(id=4, router=wrong_device.name, state=EventState.OPEN, ifindex=port.ifindex)


@pytest.fixture
def exact_pm(device) -> PlannedMaintenance:
    return PlannedMaintenance(
        start_time=datetime.datetime.now() - datetime.timedelta(days=1),
        end_time=datetime.datetime.now() + datetime.timedelta(days=1),
        type="device",
        match_type="exact",
        match_expression=device.name,
        match_device=None,
    )


@pytest.fixture
def regexp_pm(request, device, port) -> PlannedMaintenance:
    pm = PlannedMaintenance(
        start_time=datetime.datetime.now() - datetime.timedelta(days=1),
        end_time=datetime.datetime.now() + datetime.timedelta(days=1),
        type=request.param,
        match_type="regexp",
        match_expression="expression",
        match_device=None,
    )
    if request.param == "device":
        pm.match_expression = device.name
    elif request.param == "portstate":
        pm.match_expression = port.ifdescr
    return pm


@pytest.fixture
def str_pm(request, device, port) -> PlannedMaintenance:
    pm = PlannedMaintenance(
        start_time=datetime.datetime.now() - datetime.timedelta(days=1),
        end_time=datetime.datetime.now() + datetime.timedelta(days=1),
        type=request.param,
        match_type="str",
        match_expression="",
        match_device=None,
    )
    if request.param == "device":
        pm.match_expression = device.name
    elif request.param == "portstate":
        pm.match_expression = port.ifdescr
    return pm


@pytest.fixture
def intf_regex_pm(device, port) -> PlannedMaintenance:
    return PlannedMaintenance(
        start_time=datetime.datetime.now() - datetime.timedelta(days=1),
        end_time=datetime.datetime.now() + datetime.timedelta(days=1),
        type="portstate",
        match_type="intf-regexp",
        match_expression=port.ifdescr,
        match_device=device.name,
    )
