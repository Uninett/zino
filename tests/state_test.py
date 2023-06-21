import json
import logging
import os
from json import JSONDecodeError

import pytest

from zino import state


@pytest.mark.asyncio
async def test_dump_state_to_log_should_dump_to_log(caplog):
    with caplog.at_level(logging.DEBUG):
        await state.dump_state_to_log()
    assert "Dumping state" in caplog.text


@pytest.mark.asyncio
async def test_dump_state_to_file_should_dump_valid_json_to_file(tmp_path):
    dumpfile = tmp_path / "dump.json"
    await state.dump_state_to_file(dumpfile)

    assert os.path.exists(dumpfile)
    with open(dumpfile, "r") as data:
        assert json.load(data)


class TestLoadStateFromFile:
    def test_should_raise_on_invalid_json(self, invalid_state_file):
        with pytest.raises(JSONDecodeError):
            state.load_state_from_file(str(invalid_state_file))

    def test_should_replace_global_state(self, valid_state_file):
        assert state.events.last_event_id == 0
        state.load_state_from_file(str(valid_state_file))
        assert state.events.last_event_id == 42

    def test_should_do_nothing_when_state_file_is_missing(self, tmp_path):
        fake_file = tmp_path / "nonexistent.json"
        original_last_event_id = state.events.last_event_id
        state.load_state_from_file(str(fake_file))
        assert state.events.last_event_id == original_last_event_id


#
# Fixtures
#


@pytest.fixture
def valid_state_file(tmp_path):
    state_filename = tmp_path / "dump.json"
    with open(state_filename, "w") as statefile:
        statefile.write("""{ "events": {}, "last_event_id": 42 }""")
    return state_filename


@pytest.fixture
def invalid_state_file(tmp_path):
    state_filename = tmp_path / "invalid-dump.json"
    with open(state_filename, "w") as state_file:
        state_file.write("{....")
    return state_filename
