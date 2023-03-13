from zino import scheduler


def test_scheduler_should_be_initialized_without_error():
    sched = scheduler.get_scheduler()
    assert sched
