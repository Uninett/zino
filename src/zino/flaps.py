"""Implements data models and algorithms for tracking interface flapping.

Flapping is normally only tracked/updated based on incoming link traps.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Tuple

from pydantic import BaseModel, BeforeValidator, Field, PlainSerializer
from typing_extensions import Annotated

from zino.config.models import PollDevice
from zino.statemodels import FlapState, InterfaceState, PortStateEvent

if TYPE_CHECKING:
    from zino.state import ZinoState

from zino.time import now

_logger = logging.getLogger(__name__)

# Constants from Zino 1
FLAP_THRESHOLD = 35
FLAP_CEILING = 256
FLAP_MIN = 1.5
FLAP_MULTIPLIER = 2
FLAP_INIT_VAL = 2
FLAP_DECREMENT = 0.5
FLAP_DECREMENT_INTERVAL_SECONDS = 300

DeviceName = str
InterfaceIndex = int
PortIndex = Annotated[
    Tuple[DeviceName, InterfaceIndex],
    # Apply customized Pydantic serializing logic to the tuple, which will be used as dict keys
    PlainSerializer(lambda x: f"{x[0]}:{x[1]}", return_type=str, when_used="json"),
    BeforeValidator(lambda x: x.split(":") if isinstance(x, str) else x),
]


class FlappingState(BaseModel):
    """Contains runtime flapping stats for a single port"""

    hist_val: float = FLAP_INIT_VAL
    first_flap: datetime = Field(default_factory=now)
    last_flap: datetime = Field(default_factory=now)
    flaps: int = 0
    last_age: Optional[datetime] = None
    flapped_above_threshold: bool = False
    in_active_flap_state: bool = False

    def update(self):
        """Updates flap stats for a single port.  Called when a link trap is processed."""
        self.age()
        new_histval = min(self.hist_val * FLAP_MULTIPLIER, FLAP_CEILING)
        self.hist_val = new_histval
        self.flaps += 1
        self.last_flap = now()

    def age(self):
        """Ages the flapping state of a port.

        This should be idempotent, i.e. it is time dependent and can be called whenever one pleases to update the
        flap statistics of a port.
        """
        timestamp = now()

        last = self.last_age or self.last_flap
        delta = (timestamp - last).total_seconds() / FLAP_DECREMENT_INTERVAL_SECONDS
        self.last_age = timestamp
        new_hist_val = self.hist_val ** (FLAP_DECREMENT**delta)
        self.hist_val = min(new_hist_val, FLAP_CEILING)

    def is_below_threshold(self):
        """Returns True if the current flap value is below the flapping threshold"""
        return self.hist_val < FLAP_THRESHOLD


class FlappingStates(BaseModel):
    """Contains all runtime stats for flapping states"""

    interfaces: dict[PortIndex, FlappingState] = {}

    def update_interface_flap(self, interface: PortIndex):
        """Updates the flapping stats for a port.

        If the port is not already being tracked, it initializes the stats for it.
        """
        if interface not in self.interfaces:
            self.first_flap(interface)
            return

        flap = self.interfaces[interface]
        flap.update()

    def first_flap(self, interface: PortIndex) -> FlappingState:
        """Initializes flapping stats for a port the first time a link trap is received for it"""
        flap = FlappingState(
            hist_val=FLAP_INIT_VAL,
            flaps=1,
        )
        self.interfaces[interface] = flap
        return flap

    def unflap(self, interface: PortIndex) -> FlappingState:
        """Removes all flapping stats tracking for a port"""
        return self.interfaces.pop(interface)

    def is_flapping(self, interface: PortIndex) -> bool:
        """Returns True if the current stats indicate that the interface has crossed the flapping threshold.

        This is not the same as 'a flapping state has been declared', but is an indicator that such a state could
        now be declared.
        """
        if interface not in self.interfaces:
            return False

        flap = self.interfaces[interface]
        flap.age()
        if flap.hist_val < FLAP_MIN:
            return False
        if flap.hist_val > FLAP_THRESHOLD:
            flap.flapped_above_threshold = True
        if flap.flapped_above_threshold:
            return True
        return False

    def was_flapping(self, interface: PortIndex) -> bool:
        """Seems to answer whether there exists any flapping tracking stats for a port from before"""
        return interface in self.interfaces

    def get_flap_count(self, interface: PortIndex) -> int:
        """Returns the current flap count of an interface, or 0 if no flapping stats exist for it."""
        if interface not in self.interfaces:
            return 0
        return self.interfaces[interface].flaps

    def get_flap_value(self, interface: PortIndex) -> float:
        """Returns the current flap value of an interface, or 0 if no flapping stats exist for it."""
        if interface not in self.interfaces:
            return 0
        return self.interfaces[interface].hist_val


async def age_flapping_states(state: ZinoState, polldevs: dict[str, PollDevice]):
    """Ages all flapping states in the given ZinoState.  Should be called every FLAP_DECREMENT_INTERVAL_SECONDS."""
    for index, flap in state.flapping.interfaces.items():
        await age_single_interface_flapping_state(flap, index, state, polldevs)


async def age_single_interface_flapping_state(
    flap: FlappingState, index: PortIndex, state: ZinoState, polldevs: dict[str, PollDevice]
) -> None:
    """Ages a single interface's flapping state, and updates events if it is no longer flapping."""
    flap.age()
    router, ifindex = index
    polldev = polldevs.get(router)
    port = state.devices.get(router).ports.get(ifindex) if router in state.devices else None
    if flap.is_below_threshold():
        # Flapping stats aged below threshold, interface is no longer considered flapping
        if state.flapping.was_flapping(index):
            if port:
                msg = f'{router}: intf "{port.ifdescr}" ix {ifindex} stopped flapping (aging)'
            else:
                msg = f"{router}: ix {ifindex} stopped flapping (aging)"
            _logger.info(msg)

            # An operator may have closed a flapping port event prematurely, so we may need to update both the closed
            # event and an open event, following Zino 1 logic:
            events: List[PortStateEvent] = []
            if event := state.events.get_closed_event(router, ifindex, PortStateEvent):
                events.append(event)
            if event := state.events.get_or_create_event(router, ifindex, PortStateEvent):
                events.append(event)
            for event in events:
                # If we don't have all the necessary information, revisit later (this could mean that this was called
                # just after process startup, before config or state was properly loaded)
                if not (polldev and polldev.address and polldev.priority and port):
                    continue

                # Original Zino comment says: Hm, if this is a new event, we need to set "state" and "opened".
                event.flapstate = FlapState.STABLE
                event.flaps = state.flapping.get_flap_count(index)
                event.port = port.ifdescr
                event.portstate = port.state
                event.router = router
                event.polladdr = polldev.address
                event.priority = polldev.priority
                event.ifindex = ifindex
                event.descr = port.ifalias

                event.add_log(msg)

                state.events.commit(event)

            old_state = port.state
            port.state = InterfaceState.FLAPPING

            # Local import to avoid circular import
            from zino.tasks.linkstatetask import LinkStateTask

            poll = LinkStateTask(device=polldev, state=state)
            try:
                await poll.poll_single_interface(ifindex)
            except Exception:  # noqa
                port.state = old_state

        state.flapping.unflap(index)
