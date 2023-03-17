from zino.jobs.reachablejob import ReachableJob

REGISTERED_JOBS = [ReachableJob]


async def run_all_jobs(device):
    for job in REGISTERED_JOBS:
        await job.run_job(device)
