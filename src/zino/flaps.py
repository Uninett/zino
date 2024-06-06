"""Implements data models and algorithms for tracking interface flapping.

Flapping is normally only tracked/updated based on incoming link traps.
"""

from datetime import datetime
from typing import Optional, Tuple

from pydantic import BaseModel, Field

from zino.time import now

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
PortIndex = Tuple[DeviceName, InterfaceIndex]


class FlappingState(BaseModel):
    """Contains runtime flapping stats for a single port"""

    hist_val: float = FLAP_INIT_VAL
    first_flap: datetime = Field(default_factory=now)
    last_flap: datetime = Field(default_factory=now)
    flaps: int = 0
    last_age: Optional[datetime] = None
    flapped_above_threshold: bool = False
    flapping: bool = False

    def update(self):
        """Updates flap stats for a single port.  Called when a link trap is processed."""
        self.age()
        new_histval = min(self.hist_val * FLAP_MULTIPLIER, FLAP_CEILING)
        self.hist_val = new_histval
        self.flaps += 1
        self.last_flap = now()

    def age(self):
        """Ages the flapping state of a port"""
        timestamp = now()

        last = self.last_age or self.last_flap
        delta = (timestamp - last).total_seconds() / FLAP_DECREMENT_INTERVAL_SECONDS
        self.last_age = timestamp
        new_hist_val = self.hist_val ** (FLAP_DECREMENT**delta)
        self.hist_val = min(new_hist_val, FLAP_CEILING)


class FlappingStates(BaseModel):
    """Contains all runtime stats for flapping states"""

    interfaces: dict[PortIndex, FlappingState] = {}

    def update_interface_flap(self, interface: PortIndex):
        if interface not in self.interfaces:
            self.first_flap(interface)
            return

        flap = self.interfaces[interface]
        flap.update()

    def first_flap(self, interface: PortIndex) -> FlappingState:
        flap = FlappingState(
            hist_val=FLAP_INIT_VAL,
            flaps=1,
        )
        self.interfaces[interface] = flap
        return flap

    def unflap(self, interface: PortIndex) -> FlappingState:
        return self.interfaces.pop(interface)

    def is_flapping(self, interface: PortIndex) -> bool:
        if interface not in self.interfaces:
            flap = FlappingState(hist_val=0)
        else:
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


# TODO: Implement a flap ager job that ages all flapping states every FLAP_DECR_INTERVAL seconds
