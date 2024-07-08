"""This module implements handling of BFD session traps.

bfdSessUp and bfdSessDown traps only tell which BFD sessions have changed state and why, but does not actually include
the new state value for the session.  This means most of this observer's work is to just kick off a BFDTask to poll the
individual session(s) that have changed state and ensure state and events are updated accordingly.

Example of test trap message:

 snmptrap -v 2c -c public localhost:1162 "" \
     BFD-STD-MIB::bfdSessDown \
     BFD-STD-MIB::bfdSessDiag.1 u 5 \
     BFD-STD-MIB::bfdSessDiag.5 u 5

"""

import logging
from pprint import pformat
from typing import Optional

from zino.tasks.bfdtask import BFDTask
from zino.trapd import TrapMessage, TrapObserver

_logger = logging.getLogger(__name__)


class BFDTrapObserver(TrapObserver):
    WANTED_TRAPS = {
        ("BFD-STD-MIB", "bfdSessUp"),
        ("BFD-STD-MIB", "bfdSessDown"),
    }

    async def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        try:
            affected_indexes = self._parse_trap(trap)
        except ValueError:
            return

        device = trap.agent.device
        polldev = self.polldevs.get(device.name)
        if not polldev:
            _logger.error("%s: No polldevs config, ignoring BFD trap", device.name)
            return False

        updater = BFDTask(device=polldev, state=self.state)
        for bfd_session_index in affected_indexes:
            await updater.run(bfd_session_index)

        return False

    def _parse_trap(self, trap: TrapMessage) -> range:
        _logger.debug("%s: %s variables:\n%s", trap.agent.device.name, trap.name, pformat(trap.variables))

        bfd_sess_diags = trap.get_all("bfdSessDiag")
        if len(bfd_sess_diags) < 2:
            msg = f"{trap.agent.device.name} sent malformed BFD trap (less than two bfdSessDiag values)"
            _logger.error(msg)
            raise ValueError(msg)

        lower_index = min(var.instance[0] for var in bfd_sess_diags)
        upper_index = max(var.instance[0] for var in bfd_sess_diags)
        _logger.debug(
            "%s: BFD session %s affects indexes %s..%s", trap.agent.device.name, trap.name, lower_index, upper_index
        )
        affected_indexes = range(lower_index, upper_index + 1)
        return affected_indexes
