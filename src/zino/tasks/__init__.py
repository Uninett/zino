async def run_all_tasks(device):
    for task_class in get_registered_tasks():
        task = task_class(device)
        await task.run()


def get_registered_tasks():
    from zino.tasks.reachabletask import ReachableTask
    from zino.tasks.vendor import VendorTask

    return [ReachableTask, VendorTask]
