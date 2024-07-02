from datetime import timedelta

from zino.flaps import FLAP_CEILING, FLAP_THRESHOLD, FlappingState
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
