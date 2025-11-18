"""Track running jobs in APScheduler for monitoring purposes."""

import asyncio
import logging
import signal
from datetime import datetime
from typing import Optional

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_SUBMITTED,
    JobExecutionEvent,
    JobSubmissionEvent,
)

_log = logging.getLogger(__name__)


class JobTracker:
    """Tracks currently running jobs and their execution times."""

    def __init__(self):
        self.running_jobs: dict[str, dict] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def setup_signal_handler(self, loop: asyncio.AbstractEventLoop):
        """Setup SIGUSR1 signal handler for debugging using asyncio."""
        self.loop = loop
        # Use asyncio's add_signal_handler for proper event loop integration
        loop.add_signal_handler(signal.SIGUSR1, self._handle_sigusr1)
        _log.debug("SIGUSR1 handler registered for job tracking")

    def _format_duration(self, total_seconds):
        """Format duration as [Dd ]HH:MM:SS.mmm"""
        days = int(total_seconds // 86400)
        remaining = total_seconds % 86400
        hours = int(remaining // 3600)
        remaining = remaining % 3600
        minutes = int(remaining // 60)
        seconds = remaining % 60

        if days > 0:
            return f"{days}d {hours:02d}:{minutes:02d}:{seconds:06.3f}"
        else:
            return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

    def _handle_sigusr1(self):
        """Handle SIGUSR1 signal by logging currently running jobs."""
        _log.info("=" * 80)
        _log.info("SIGUSR1: Current running jobs report")
        _log.info("=" * 80)

        if not self.running_jobs:
            _log.info("No jobs currently running")
        else:
            _log.info(f"Total running jobs: {len(self.running_jobs)}")
            _log.info("")

            # Prepare table data
            current_time = datetime.now()
            rows = []

            for job_id, info in self.running_jobs.items():
                start_time = info["start_time"]
                duration_seconds = (current_time - start_time).total_seconds()

                rows.append(
                    {
                        "job_id": job_id,
                        "duration_seconds": duration_seconds,
                        "duration": self._format_duration(duration_seconds),
                        "started": start_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    }
                )

            # Sort by duration (longest running first)
            rows.sort(key=lambda x: x["duration_seconds"], reverse=True)

            # Calculate column widths
            job_width = max(len("Job ID"), max(len(r["job_id"]) for r in rows))
            dur_width = max(len("Duration"), max(len(r["duration"]) for r in rows))
            start_width = max(len("Started"), len("YYYY-MM-DD HH:MM:SS.mmm"))

            # Print header
            header = f"{'Job ID':<{job_width}} | {'Duration':>{dur_width}} | {'Started':<{start_width}}"
            _log.info(header)
            _log.info("-" * len(header))

            # Print rows
            for row in rows:
                _log.info(
                    f"{row['job_id']:<{job_width}} | {row['duration']:>{dur_width}} | {row['started']:<{start_width}}"
                )

        _log.info("=" * 80)

    def on_job_submitted(self, event: JobSubmissionEvent):
        """Track when a job starts executing."""
        job_id = event.job_id
        # Jobs can have multiple scheduled run times if they were missed
        scheduled_time = event.scheduled_run_times[0] if event.scheduled_run_times else datetime.now()

        self.running_jobs[job_id] = {
            "start_time": datetime.now(),
            "scheduled_run_time": scheduled_time,
            "jobstore": event.jobstore,
        }
        _log.debug(f"Job {job_id} started execution")

    def on_job_executed(self, event: JobExecutionEvent):
        """Track when a job completes execution."""
        job_id = event.job_id
        if job_id in self.running_jobs:
            start_time = self.running_jobs[job_id]["start_time"]
            duration = (datetime.now() - start_time).total_seconds()
            _log.debug(f"Job {job_id} completed execution after {duration:.2f}s")
            del self.running_jobs[job_id]

    def on_job_error(self, event: JobExecutionEvent):
        """Track when a job fails with an error."""
        job_id = event.job_id
        if job_id in self.running_jobs:
            start_time = self.running_jobs[job_id]["start_time"]
            duration = (datetime.now() - start_time).total_seconds()
            _log.debug(f"Job {job_id} failed with error after {duration:.2f}s: {event.exception}")
            del self.running_jobs[job_id]

    def register_with_scheduler(self, scheduler):
        """Register event listeners with the scheduler."""
        scheduler.add_listener(self.on_job_submitted, EVENT_JOB_SUBMITTED)
        scheduler.add_listener(self.on_job_executed, EVENT_JOB_EXECUTED)
        scheduler.add_listener(self.on_job_error, EVENT_JOB_ERROR)
        _log.debug("Job tracker registered with scheduler")


# Global instance
_job_tracker: Optional[JobTracker] = None


def get_job_tracker() -> JobTracker:
    """Get or create the global job tracker singleton."""
    global _job_tracker
    if _job_tracker is None:
        _job_tracker = JobTracker()
    return _job_tracker
