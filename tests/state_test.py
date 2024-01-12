import json
import os
from json import JSONDecodeError

import pytest

from zino.state import ZinoState


def test_dump_state_to_file_should_dump_valid_json_to_file(tmp_path):
    dumpfile = tmp_path / "dump.json"
    state = ZinoState()
    state.dump_state_to_file(dumpfile)

    assert os.path.exists(dumpfile)
    with open(dumpfile, "r") as data:
        assert json.load(data)


class TestLoadStateFromFile:
    def test_should_raise_on_invalid_json(self, invalid_state_file):
        with pytest.raises(JSONDecodeError):
            ZinoState.load_state_from_file(str(invalid_state_file))

    def test_should_load_saved_state(self, valid_state_file):
        state = ZinoState.load_state_from_file(str(valid_state_file))
        assert state.events.last_event_id == 42

    def test_should_return_none_when_state_file_is_missing(self, tmp_path):
        fake_file = tmp_path / "nonexistent.json"
        assert ZinoState.load_state_from_file(str(fake_file)) is None


#
# Fixtures
#


@pytest.fixture
def valid_state_file(tmp_path):
    state_filename = tmp_path / "dump.json"
    with open(state_filename, "w") as statefile:
        statefile.write(
            """
        {
          "devices": {
            "devices": {}
          },
          "events": {
            "events": {},
            "last_event_id": 42
          }
        }
        """
        )
    return state_filename


@pytest.fixture
def invalid_state_file(tmp_path):
    state_filename = tmp_path / "invalid-dump.json"
    with open(state_filename, "w") as state_file:
        state_file.write("{....")
    return state_filename
