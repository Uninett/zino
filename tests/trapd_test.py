import asyncio
import logging
import shutil

import pytest

from zino.trapd import TrapReceiver


class TestTrapReceiver:
    def test_add_community_should_accept_same_community_multiple_times(self):
        receiver = TrapReceiver()
        receiver.add_community("public")
        receiver.add_community("public")
        assert len(receiver._communities) == 1

    @pytest.mark.skipif(not shutil.which("snmptrap"), reason="Cannot find snmptrap command line program")
    @pytest.mark.asyncio
    async def test_should_log_incoming_trap(self, event_loop, caplog):
        receiver = TrapReceiver(address="127.0.0.1", port=1162, loop=event_loop)
        receiver.add_community("public")
        try:
            await receiver.open()

            cold_start = ".1.3.6.1.6.3.1.1.5.1"
            sysname_0 = ".1.3.6.1.2.1.1.5.0"
            with caplog.at_level(logging.DEBUG):
                proc = await asyncio.create_subprocess_shell(
                    f"snmptrap -v 2c -c public localhost:1162 '' {cold_start} {sysname_0} s 'MockDevice'"
                )
                await proc.communicate()
                assert proc.returncode == 0, "snmptrap command exited with error"

                assert "1.3.6.1.2.1.1.5.0 = MockDevice" in caplog.text
        finally:
            receiver.close()
