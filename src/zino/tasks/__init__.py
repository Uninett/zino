async def run_all_tasks(device, state):
    for task_class in get_registered_tasks():
        task = task_class(device, state)
        await task.run()


def get_registered_tasks():
    from zino.tasks.juniperalarmtask import JuniperAlarmTask
    from zino.tasks.linkstatetask import LinkStateTask
    from zino.tasks.reachabletask import ReachableTask
    from zino.tasks.vendor import VendorTask

    return [ReachableTask, VendorTask, LinkStateTask, JuniperAlarmTask]
