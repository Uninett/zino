from zino.tasks import get_registered_tasks


def test_task_registry_should_be_populated_by_default():
    tasks = get_registered_tasks()
    assert len(tasks) > 0
