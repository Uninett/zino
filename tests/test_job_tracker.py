"""Test suite for the JobTracker component."""

import asyncio
import signal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_MISSED,
    EVENT_JOB_SUBMITTED,
    JobExecutionEvent,
    JobSubmissionEvent,
)

from zino.job_tracker import JobTracker, get_job_tracker


class TestJobTracker:
    """Test the JobTracker class functionality."""

    @pytest.fixture
    def mock_scheduler(self):
        """Create a mock scheduler."""
        scheduler = Mock()
        scheduler.get_job = Mock(return_value=None)
        return scheduler

    def test_setup_signal_handler_should_register_sigusr1_with_event_loop(self):
        """Test setting up signal handler for SIGUSR1."""
        job_tracker = JobTracker()
        mock_loop = Mock(spec=asyncio.AbstractEventLoop)
        job_tracker.setup_signal_handler(mock_loop)

        assert job_tracker.loop == mock_loop
        mock_loop.add_signal_handler.assert_called_once_with(signal.SIGUSR1, job_tracker._handle_sigusr1)

    def test_when_no_scheduler_is_set_get_job_name_should_return_none(self):
        """Test _get_job_name when no scheduler is set."""
        job_tracker = JobTracker()
        assert job_tracker._get_job_name("job123") is None

    def test_when_scheduler_has_job_get_job_name_should_return_name(self, mock_scheduler):
        """Test _get_job_name when scheduler is available."""
        job_tracker = JobTracker()
        mock_job = Mock()
        mock_job.name = "TestJobName"
        mock_scheduler.get_job.return_value = mock_job

        job_tracker.scheduler = mock_scheduler
        result = job_tracker._get_job_name("job123")

        assert result == "TestJobName"
        mock_scheduler.get_job.assert_called_once_with("job123")

    def test_when_scheduler_raises_exception_get_job_name_should_return_none(self, mock_scheduler):
        """Test _get_job_name when scheduler raises an exception."""
        job_tracker = JobTracker()
        mock_scheduler.get_job.side_effect = Exception("Scheduler error")

        job_tracker.scheduler = mock_scheduler
        result = job_tracker._get_job_name("job123")

        assert result is None

    def test_format_duration_should_format_seconds_without_days(self):
        """Test formatting duration less than a day."""
        job_tracker = JobTracker()
        assert job_tracker._format_duration(0) == "00:00:00.000"
        assert job_tracker._format_duration(1.5) == "00:00:01.500"
        assert job_tracker._format_duration(61.123) == "00:01:01.123"
        assert job_tracker._format_duration(3661.456) == "01:01:01.456"
        assert job_tracker._format_duration(3600 * 23 + 3599.999) == "23:59:59.999"

    def test_format_duration_should_include_days_when_over_24_hours(self):
        """Test formatting duration with days."""
        job_tracker = JobTracker()
        assert job_tracker._format_duration(86400) == "1d 00:00:00.000"
        assert job_tracker._format_duration(90061.5) == "1d 01:01:01.500"
        assert job_tracker._format_duration(86400 * 10 + 7200 + 180 + 1.234) == "10d 02:03:01.234"

    @patch("zino.job_tracker.datetime")
    @patch("zino.job_tracker._log")
    def test_when_no_jobs_executing_sigusr1_should_log_empty_message(self, mock_log, mock_datetime):
        """Test SIGUSR1 handler when no jobs are running."""
        job_tracker = JobTracker()
        mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)

        job_tracker._handle_sigusr1()

        # Check that it logs "No jobs currently running"
        mock_log.info.assert_any_call("No jobs currently running")

    @patch("zino.job_tracker.datetime")
    @patch("zino.job_tracker._log")
    def test_when_jobs_are_executing_sigusr1_should_log_jobs(self, mock_log, mock_datetime):
        """Test SIGUSR1 handler with running jobs."""
        job_tracker = JobTracker()
        # Set up mock time
        current_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = current_time

        # Add some running jobs with different characteristics
        job_tracker.running_jobs = {
            "job1": {
                "start_time": current_time - timedelta(seconds=120),
                "job_name": "TestJob1",
            },
            "job2": {
                "start_time": current_time - timedelta(seconds=60),
                "job_name": None,
            },
            "job3": {
                "start_time": current_time - timedelta(seconds=300),
                "job_name": "job3",  # Same as ID, should not show in parentheses
            },
        }

        job_tracker._handle_sigusr1()

        # Convert all log calls to strings for easier checking
        log_output = " ".join(str(call) for call in mock_log.info.call_args_list)

        # Verify the summary line - note it's called with a format string and argument
        mock_log.info.assert_any_call("Total running jobs: %d", 3)

        # Verify table header is logged
        assert "Job ID" in log_output and "Duration" in log_output and "Started" in log_output

        # Verify each job appears in the output
        assert "job1 (TestJob1)" in log_output, "job1 with name TestJob1 should appear"
        assert "job2" in log_output, "job2 should appear"
        assert "job3" in log_output, "job3 should appear"
        # job3 shouldn't show name in parentheses since it matches the ID
        assert "job3 (job3)" not in log_output, "job3 should not show redundant name in parentheses"

    @patch("zino.job_tracker.datetime")
    @patch("zino.job_tracker._log")
    def test_sigusr1_should_format_job_table_sorted_by_duration(self, mock_log, mock_datetime):
        """Test the formatted output of SIGUSR1 handler is sorted by duration."""
        job_tracker = JobTracker()
        current_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = current_time

        # Add jobs with varying durations
        job_tracker.running_jobs = {
            "job1": {
                "start_time": current_time - timedelta(days=1, hours=2, minutes=30, seconds=45.123),
                "job_name": "LongRunningTask",
            },
            "job2": {
                "start_time": current_time - timedelta(minutes=5, seconds=30.5),
                "job_name": "QuickTask",
            },
            "job3": {
                "start_time": current_time - timedelta(hours=1),
                "job_name": None,
            },
        }

        job_tracker._handle_sigusr1()

        # Verify the summary line with parametrized logging
        mock_log.info.assert_any_call("Total running jobs: %d", 3)

        # Verify the output includes all jobs and is properly formatted
        info_calls = [str(call) for call in mock_log.info.call_args_list]
        output = "\n".join(info_calls)
        assert "Job ID" in output
        assert "Duration" in output
        assert "Started" in output
        assert "LongRunningTask" in output
        assert "QuickTask" in output

        # Verify jobs are sorted by duration (longest first)
        # Find the positions of each job in the output
        longrunning_pos = output.find("LongRunningTask")
        job3_pos = output.find("job3")
        quicktask_pos = output.find("QuickTask")

        # All jobs should be present
        assert longrunning_pos != -1, "LongRunningTask not found in output"
        assert job3_pos != -1, "job3 not found in output"
        assert quicktask_pos != -1, "QuickTask not found in output"

        # Verify order: LongRunningTask (1d 2h) should come before job3 (1h) which should come before QuickTask (5m)
        assert longrunning_pos < job3_pos, "LongRunningTask should appear before job3 (sorted by duration)"
        assert job3_pos < quicktask_pos, "job3 should appear before QuickTask (sorted by duration)"

    def test_on_job_submitted_should_track_new_job(self, mock_scheduler):
        """Test tracking when a new job starts."""
        job_tracker = JobTracker()
        job_tracker.scheduler = mock_scheduler

        # Create mock job with name attribute properly set
        mock_job = Mock()
        mock_job.name = "TestJob"
        mock_scheduler.get_job.return_value = mock_job

        event = Mock(spec=JobSubmissionEvent)
        event.job_id = "job123"
        event.scheduled_run_times = [datetime(2024, 1, 1, 10, 0, 0)]
        event.jobstore = "default"

        job_tracker.on_job_submitted(event)

        assert "job123" in job_tracker.running_jobs
        assert job_tracker.running_jobs["job123"]["scheduled_run_time"] == datetime(2024, 1, 1, 10, 0, 0)
        assert job_tracker.running_jobs["job123"]["jobstore"] == "default"
        assert job_tracker.running_jobs["job123"]["job_name"] == "TestJob"
        assert "start_time" in job_tracker.running_jobs["job123"]

    def test_when_job_already_running_on_job_submitted_should_not_update(self):
        """Test when a job is submitted but already in running list."""
        job_tracker = JobTracker()
        job_tracker.running_jobs["job123"] = {"start_time": datetime.now()}

        event = Mock(spec=JobSubmissionEvent)
        event.job_id = "job123"
        event.scheduled_run_times = [datetime.now()]
        event.jobstore = "default"

        original_info = job_tracker.running_jobs["job123"]
        job_tracker.on_job_submitted(event)

        # Should not update the existing entry
        assert job_tracker.running_jobs["job123"] == original_info

    @patch("zino.job_tracker.datetime")
    def test_when_no_scheduled_time_on_job_submitted_should_use_current_time(self, mock_datetime):
        """Test when job has no scheduled run times."""
        job_tracker = JobTracker()
        current_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = current_time

        event = Mock(spec=JobSubmissionEvent)
        event.job_id = "job123"
        event.scheduled_run_times = []
        event.jobstore = "default"

        job_tracker.on_job_submitted(event)

        assert "job123" in job_tracker.running_jobs
        assert job_tracker.running_jobs["job123"]["scheduled_run_time"] == current_time

    @patch("zino.job_tracker.datetime")
    def test_on_job_executed_should_remove_job_from_running(self, mock_datetime):
        """Test tracking when a job completes successfully."""
        job_tracker = JobTracker()
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 10)
        mock_datetime.now.side_effect = [end_time]

        job_tracker.running_jobs["job123"] = {"start_time": start_time}

        event = Mock(spec=JobExecutionEvent)
        event.job_id = "job123"

        job_tracker.on_job_executed(event)

        assert "job123" not in job_tracker.running_jobs

    def test_when_job_not_tracked_on_job_executed_should_not_raise(self):
        """Test job execution event for job not in running list."""
        job_tracker = JobTracker()
        event = Mock(spec=JobExecutionEvent)
        event.job_id = "job123"

        # Should not raise an exception
        job_tracker.on_job_executed(event)
        assert "job123" not in job_tracker.running_jobs

    @patch("zino.job_tracker.datetime")
    def test_on_job_error_should_remove_job_from_running(self, mock_datetime):
        """Test tracking when a job fails with error."""
        job_tracker = JobTracker()
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 10)
        mock_datetime.now.side_effect = [end_time]

        job_tracker.running_jobs["job123"] = {"start_time": start_time}

        event = Mock(spec=JobExecutionEvent)
        event.job_id = "job123"
        event.exception = Exception("Test error")

        job_tracker.on_job_error(event)

        assert "job123" not in job_tracker.running_jobs

    def test_when_job_not_tracked_on_job_error_should_not_raise(self):
        """Test job error event for job not in running list."""
        job_tracker = JobTracker()
        event = Mock(spec=JobExecutionEvent)
        event.job_id = "job123"
        event.exception = Exception("Test error")

        # Should not raise an exception
        job_tracker.on_job_error(event)
        assert "job123" not in job_tracker.running_jobs

    def test_when_missed_job_in_running_list_it_should_be_removed(self):
        """Test when a missed job is unexpectedly in running list."""
        job_tracker = JobTracker()
        job_tracker.running_jobs["job123"] = {"start_time": datetime.now()}

        event = Mock(spec=JobExecutionEvent)
        event.job_id = "job123"

        job_tracker.on_job_missed(event)

        assert "job123" not in job_tracker.running_jobs

    def test_when_job_missed_it_should_not_be_in_running_list(self):
        """Test normal case of missed job not in running list."""
        job_tracker = JobTracker()
        event = Mock(spec=JobExecutionEvent)
        event.job_id = "job123"

        job_tracker.on_job_missed(event)
        assert "job123" not in job_tracker.running_jobs

    @patch("zino.job_tracker.datetime")
    def test_when_max_instances_reached_running_job_should_remain_tracked(self, mock_datetime):
        """Test max_instances event when job is running."""
        job_tracker = JobTracker()
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        current_time = datetime(2024, 1, 1, 12, 5, 0)
        mock_datetime.now.return_value = current_time

        job_tracker.running_jobs["job123"] = {"start_time": start_time}

        event = Mock(spec=JobExecutionEvent)
        event.job_id = "job123"

        job_tracker.on_job_max_instances(event)

        # Job should still be in running list
        assert "job123" in job_tracker.running_jobs
        assert job_tracker.running_jobs["job123"]["start_time"] == start_time

    def test_when_max_instances_reached_for_untracked_job_it_should_stay_untracked(self):
        """Test max_instances event when job is not in running list."""
        job_tracker = JobTracker()
        event = Mock(spec=JobExecutionEvent)
        event.job_id = "job123"

        job_tracker.on_job_max_instances(event)
        assert "job123" not in job_tracker.running_jobs

    def test_register_with_scheduler_should_add_all_event_listeners(self, mock_scheduler):
        """Test registering tracker with scheduler."""
        job_tracker = JobTracker()
        job_tracker.register_with_scheduler(mock_scheduler)

        assert job_tracker.scheduler == mock_scheduler
        assert mock_scheduler.add_listener.call_count == 5

        # Check each listener registration
        calls = mock_scheduler.add_listener.call_args_list
        assert calls[0][0][0] == job_tracker.on_job_submitted
        assert calls[0][0][1] == EVENT_JOB_SUBMITTED
        assert calls[1][0][0] == job_tracker.on_job_executed
        assert calls[1][0][1] == EVENT_JOB_EXECUTED
        assert calls[2][0][0] == job_tracker.on_job_error
        assert calls[2][0][1] == EVENT_JOB_ERROR
        assert calls[3][0][0] == job_tracker.on_job_missed
        assert calls[3][0][1] == EVENT_JOB_MISSED
        assert calls[4][0][0] == job_tracker.on_job_max_instances
        assert calls[4][0][1] == EVENT_JOB_MAX_INSTANCES


class TestJobTrackerSingleton:
    """Test the singleton pattern for JobTracker."""

    def test_get_job_tracker_should_create_singleton_instance(self):
        """Test that get_job_tracker creates a singleton instance."""
        # Reset the global variable first
        import zino.job_tracker

        zino.job_tracker._job_tracker = None

        tracker1 = get_job_tracker()
        tracker2 = get_job_tracker()

        assert tracker1 is tracker2
        assert isinstance(tracker1, JobTracker)

    def test_get_job_tracker_should_reuse_existing_instance(self):
        """Test that get_job_tracker reuses existing instance."""
        import zino.job_tracker

        # Set up an existing tracker
        existing_tracker = JobTracker()
        zino.job_tracker._job_tracker = existing_tracker

        result = get_job_tracker()

        assert result is existing_tracker
