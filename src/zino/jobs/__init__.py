from zino.jobs.fauxpolljob import FauxPollJob

REGISTERED_JOBS = [FauxPollJob]

async def run_all_jobs(device):
    for job in REGISTERED_JOBS:
        await job.run_job(device)
