from zino.tasks.reachabletask import ReachableTask

REGISTERED_TASKS = [ReachableTask]


async def run_all_tasks(device):
    for job in REGISTERED_TASKS:
        await job.run_job(device)
