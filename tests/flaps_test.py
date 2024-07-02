from datetime import timedelta

from zino.flaps import (
    FLAP_CEILING,
    FLAP_INIT_VAL,
    FLAP_MIN,
    FLAP_THRESHOLD,
    FlappingState,
    FlappingStates,
)
from zino.time import now


class TestFlappingState:
    def test_update_should_increase_histval(self):
        flapping_state = FlappingState()
        initial = flapping_state.hist_val

        flapping_state.update()
        assert flapping_state.hist_val > initial

    def test_update_should_set_last_flap_timestamp(self):
        flapping_state = FlappingState()
        initial = now() - timedelta(seconds=10)
        flapping_state.last_flap = initial

        flapping_state.update()
        assert flapping_state.last_flap > initial

    def test_update_should_never_increase_hist_val_above_ceiling(self):
        flapping_state = FlappingState(hist_val=FLAP_CEILING)

        flapping_state.update()
        assert flapping_state.hist_val <= FLAP_CEILING

    def test_age_should_decrease_hist_val(self):
        flapping_state = FlappingState(hist_val=42)

        flapping_state.age()
        assert flapping_state.hist_val < 42

    def test_when_hist_val_is_below_threshold_is_below_threshold_should_return_true(self):
        flapping_state = FlappingState(hist_val=FLAP_THRESHOLD - 0.2)

        assert flapping_state.is_below_threshold()


class TestFlappingStates:
    def test_update_interface_flap_should_update_existing_flapping_state(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=42)

        flapping_states.update_interface_flap(1)
        assert flapping_states.interfaces[1].hist_val > 42

    def test_when_interface_has_no_flapping_stats_update_interface_flap_should_initialize_them(self):
        flapping_states = FlappingStates()

        flapping_states.update_interface_flap(1)
        assert 1 in flapping_states.interfaces

    def test_first_flap_should_initialize_flapping_state(self):
        flapping_states = FlappingStates()

        flapping_states.first_flap(1)
        assert flapping_states.interfaces[1].flaps == 1
        assert flapping_states.interfaces[1].hist_val == FLAP_INIT_VAL

    def test_unflap_should_remove_flapping_state(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState()

        flapping_states.unflap(1)
        assert 1 not in flapping_states.interfaces

    def test_when_hist_val_is_above_threshold_is_flapping_should_set_flag(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=FLAP_THRESHOLD + 0.2)

        flapping_states.is_flapping(1)
        assert flapping_states.interfaces[1].flapped_above_threshold

    def test_when_hist_val_is_above_threshold_is_flapping_should_return_true(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=FLAP_THRESHOLD + 0.2)

        assert flapping_states.is_flapping(1)

    def test_when_hist_val_is_below_minimal_threshold_is_flapping_should_return_false(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=FLAP_MIN - 0.2)

        assert not flapping_states.is_flapping(1)

    def test_when_flapping_stats_is_between_thresholds_is_flapping_should_return_false(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=int((FLAP_THRESHOLD + FLAP_MIN) / 2))

        assert not flapping_states.is_flapping(1)

    def test_when_flapping_stats_do_not_exist_is_flapping_should_return_false(self):
        flapping_states = FlappingStates()

        assert not flapping_states.is_flapping(1)

    def test_when_flapping_stats_exist_was_flapping_should_return_true(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState()

        assert flapping_states.was_flapping(1)

    def test_when_flapping_stats_do_not_exist_was_flapping_should_return_false(self):
        flapping_states = FlappingStates()

        assert not flapping_states.was_flapping(1)

    def test_when_flapping_stats_exist_get_flap_count_should_return_flap_count(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(flaps=42)

        assert flapping_states.get_flap_count(1) == 42

    def test_when_flapping_stats_do_not_exist_get_flap_count_should_return_zero(self):
        flapping_states = FlappingStates()

        assert flapping_states.get_flap_count(1) == 0

    def test_when_flapping_stats_exist_get_flap_value_should_return_hist_val(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=42)

        assert flapping_states.get_flap_value(1) == 42

    def test_when_flapping_stats_do_not_exist_get_flap_value_should_return_zero(self):
        flapping_states = FlappingStates()

        assert flapping_states.get_flap_value(1) == 0
