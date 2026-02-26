#!/usr/bin/env python3
import argparse
import asyncio
import errno
import gc
import grp
import logging
import logging.config
import os
import pwd
import sys
from asyncio import AbstractEventLoop
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

import tzlocal
from pydantic import ValidationError

from zino import flaps, state, version
from zino.api.server import ZinoServer
from zino.config import InvalidConfigurationError, read_configuration
from zino.job_tracker import get_job_tracker
from zino.scheduler import get_scheduler, load_and_schedule_polldevs
from zino.snmp import import_snmp_backend
from zino.snmp.agent import ZinoSnmpAgent
from zino.statemodels import Event
from zino.trapd import import_trap_backend

# ensure all our desired trap observers are loaded.  They will not be explicitly referenced here, hence the noqa tag
from zino.trapobservers import (  # noqa
    bfd_traps,
    bgp_traps,
    ignored_traps,
    link_traps,
    logged_traps,
)
from zino.utils import file_is_world_readable

STATE_DUMP_JOB_ID = "zino.dump_state"
# Never try to dump state more often than this:
MINIMUM_STATE_DUMP_INTERVAL = timedelta(seconds=10)
DEFAULT_CONFIG_FILE = "zino.toml"
_log = logging.getLogger("zino")

_dump_child_pid: int = 0


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO if not args.debug else logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s (%(threadName)s) - %(message)s",
    )
    _config = load_config(args)
    if _config:
        state.config = _config
    apply_logging_config(state.config.logging)

    try:
        secrets_file = state.config.authentication.file
        if file_is_world_readable(secrets_file):
            _log.warning(
                f"Secrets file {secrets_file} is world-readable. Please ensure that it is only readable by the user that runs the zino process."
            )
    except OSError as e:
        _log.fatal(e)
        sys.exit(1)

    # Load the same SNMP and trap back-ends
    snmp_backend = import_snmp_backend(state.config.snmp.backend)
    snmp_backend.init_backend()
    import_trap_backend(state.config.snmp.backend)

    state.state = state.ZinoState.load_state_from_file(state.config.persistence.file) or state.ZinoState()
    state.clean_state(state.state)
    init_event_loop(args)


def load_config(args: argparse.Namespace) -> Optional[state.Configuration]:
    """
    Loads the configuration file, exiting the process if there are config errors

    Returns the configuration specified by the config file and None if no config file
    name was specified as argument and no default config file exists
    """
    try:
        return read_configuration(args.config_file or DEFAULT_CONFIG_FILE, args.polldevs)
    except OSError:
        if args.config_file:
            _log.fatal(f"No config file with the name {args.config_file} found.")
            sys.exit(1)
    except InvalidConfigurationError:
        _log.fatal(f"Configuration file with the name {args.config_file or DEFAULT_CONFIG_FILE} is invalid TOML.")
        sys.exit(1)
    except ValidationError as e:
        _log.fatal(e)
        sys.exit(1)


def apply_logging_config(logging_config: dict[str, Any]) -> None:
    """Applies the logging configuration, exiting the process if there are config errors"""
    try:
        logging.config.dictConfig(logging_config)
    except ValueError as error:
        _log.fatal(f"Invalid logging configuration: {error}")
        sys.exit(1)


def init_event_loop(args: argparse.Namespace, loop: Optional[AbstractEventLoop] = None):
    if not loop:
        loop = asyncio.get_event_loop()

    if args.trap_port:
        trap_backend = import_trap_backend()
        trap_receiver = trap_backend.TrapReceiver(port=args.trap_port, loop=loop, state=state.state)
        for community in state.config.snmp.trap.require_community:
            trap_receiver.add_community(community)
        trap_receiver.auto_subscribe_observers()

        try:
            loop.run_until_complete(trap_receiver.open())
        except PermissionError:
            _log.fatal(
                "Permission denied on UDP port %s. Use --trap-port to specify unprivileged port, or run as root",
                args.trap_port,
            )
            sys.exit(errno.EACCES)
    # Drop privileges if running as root and a target user is configured
    target_user = args.user if args.user else state.config.process.user
    if os.geteuid() == 0:
        if target_user:
            switch_to_user(target_user)
        else:
            _log.warning(
                "Zino is running with root privileges. It is recommended to configure a user to drop privileges to "
                "using the --user option or the process.user setting in the configuration file."
            )

    setup_initial_job_schedule(loop, args)

    server = ZinoServer(loop=loop, state=state.state, polldevs=state.polldevs, config=state.config)
    server.serve()

    # Start SNMP agent if enabled
    if state.config.snmp.agent.enabled:
        snmp_agent = ZinoSnmpAgent(
            listen_address=state.config.snmp.agent.address,
            listen_port=state.config.snmp.agent.port,
            community=state.config.snmp.agent.community,
        )
        # Schedule the SNMP agent to start as a coroutine
        loop.create_task(snmp_agent.open())

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

    _log.info("Shutting down, performing final state dump")
    _wait_for_dump_child()
    try:
        state.state.dump_state_to_file(state.config.persistence.file)
    except Exception:
        _log.exception("Final state dump failed")

    return True


async def fork_and_dump_state(filename: str):
    """Forks a child process to dump state without blocking the event loop.

    The child inherits a COW memory snapshot and calls the regular dump_state_to_file.
    Must be a coroutine so that APScheduler's `AsyncIOExecutor` runs it on the event loop rather than in a thread
    pool, which would risk concurrent modification of state data structures during serialization.
    """
    global _dump_child_pid
    _reap_dump_child()
    if _dump_child_pid:
        _log.warning("Previous state dump (pid %d) still running, skipping", _dump_child_pid)
        return

    pid = os.fork()
    if pid == 0:  # pragma: no cover
        # Child process — serialize and exit
        try:
            state.state.dump_state_to_file(filename)
        except Exception:
            _log.exception("State dump failed in child process")
            os._exit(1)
        os._exit(0)
    else:
        _dump_child_pid = pid
        _log.debug("Forked child process %d to dump state", pid)


def _reap_dump_child():
    """Checks if the dump child process has finished and reaps it."""
    global _dump_child_pid
    if not _dump_child_pid:
        return
    try:
        pid, status = os.waitpid(_dump_child_pid, os.WNOHANG)
    except ChildProcessError:
        _dump_child_pid = 0
        return
    if pid:
        _dump_child_pid = 0
        if os.WIFEXITED(status) and os.WEXITSTATUS(status) != 0:
            _log.error("State dump child (pid %d) exited with status %d", pid, os.WEXITSTATUS(status))
        elif os.WIFSIGNALED(status):
            _log.error("State dump child (pid %d) killed by signal %d", pid, os.WTERMSIG(status))


def _wait_for_dump_child():
    """Waits (blocking) for a running dump child process to finish.

    Called during shutdown so that the final synchronous state dump does not
    race with a previously forked dump child writing to the same file.
    """
    global _dump_child_pid
    if not _dump_child_pid:
        return
    _log.debug("Waiting for dump child (pid %d) to finish before final dump", _dump_child_pid)
    try:
        os.waitpid(_dump_child_pid, 0)
    except ChildProcessError:
        pass
    _dump_child_pid = 0


def setup_initial_job_schedule(loop: AbstractEventLoop, args: argparse.Namespace) -> None:
    """Schedules all recurring and single-run jobs"""
    scheduler = get_scheduler()
    scheduler.start()

    # Register job tracker to monitor running jobs
    job_tracker = get_job_tracker()
    job_tracker.register_with_scheduler(scheduler)
    job_tracker.setup_signal_handler(loop)

    scheduler.add_job(
        func=load_and_schedule_polldevs,
        id="load_and_schedule_polldevs",
        trigger="interval",
        args=(state.config.polling.file,),
        minutes=state.config.polling.period,
        next_run_time=datetime.now(),
    )
    # Schedule state dumping as often as configured in
    # 'config.persistence.period' and reschedule whenever events are committed
    scheduler.add_job(
        func=fork_and_dump_state,
        trigger="interval",
        args=(state.config.persistence.file,),
        id=STATE_DUMP_JOB_ID,
        minutes=state.config.persistence.period,
    )

    # Schedule planned maintenance
    async def _async_update_pm_states():
        state.state.planned_maintenances.update_pm_states(state.state)

    scheduler.add_job(
        func=_async_update_pm_states,
        id="update_pm_states",
        trigger="interval",
        minutes=1,
        next_run_time=datetime.now(),
    )
    # Schedule periodic flap statistics aging
    scheduler.add_job(
        func=flaps.age_flapping_states,
        id="age_flapping_states",
        args=(state.state, state.polldevs),
        trigger="interval",
        seconds=flaps.FLAP_DECREMENT_INTERVAL_SECONDS,
        next_run_time=datetime.now(),
    )
    state.state.events.add_event_observer(reschedule_dump_state_on_commit)
    state.state.planned_maintenances.add_pm_observer(reschedule_dump_state_on_pm_change)

    # Schedule removing events that have been closed for a certain time
    async def _async_delete_expired_events():
        state.state.events.delete_expired_events()

    scheduler.add_job(
        func=_async_delete_expired_events,
        id="delete_expired_events",
        trigger="interval",
        minutes=30,
    )

    scheduler.add_job(
        func=log_snmp_session_stats,
        id="log_snmp_session_stats",
        trigger="interval",
        minutes=1,
    )

    if args.stop_in:
        _log.info("Instructed to stop in %s seconds", args.stop_in)
        scheduler.add_job(
            func=loop.stop,
            trigger="date",
            run_date=datetime.now() + timedelta(seconds=args.stop_in),
            name="Stop server on timeout",
            id="stop-process",
        )


def switch_to_user(username: str):
    """Switch the process to another user (aka. drop privileges)"""

    # Get UID/GID of current user
    old_uid = os.getuid()
    old_gid = os.getgid()

    try:
        # Try to get information about the given username
        user = pwd.getpwnam(username)
    except KeyError:
        _log.error("Could not find user %s", username)
        return False

    if old_uid == user.pw_uid:
        # Already running as the given user
        _log.debug("Already running as uid/gid %d/%d.", old_uid, old_gid)
        return True

    try:
        # Set primary group
        os.setgid(user.pw_gid)

        # Set non-primary groups
        gids = [g.gr_gid for g in grp.getgrall() if username in g.gr_mem]
        if gids:
            os.setgroups(gids)

        # Set user id
        os.setuid(user.pw_uid)
    except OSError as error:
        # Failed changing uid/gid
        _log.error(
            "Failed changing uid/gid from %d/%d to %d/%d (%s)", old_uid, old_gid, user.pw_uid, user.pw_gid, error
        )
        return False

    # Switch successful
    _log.info("Dropped privileges to user %s", username)
    _log.debug("uid/gid changed from %d/%d to %d/%d.", old_uid, old_gid, user.pw_uid, user.pw_gid)
    return True


def reschedule_dump_state_on_commit(new_event: Event, old_event: Optional[Event] = None) -> None:
    """Observer that reschedules the state dumper job whenever an event is committed and there's
    more than `MINIMUM_STATE_DUMP_INTERVAL` time until the next scheduled state dump.
    """

    reschedule_dump_state(f"event {new_event.id} committed")


def reschedule_dump_state_on_pm_change() -> None:
    """Observer that reschedules the state dumper job whenever the planned maintenance
    dict is changed and there's more than `MINIMUM_STATE_DUMP_INTERVAL` time until the next scheduled
    state dump.
    """
    reschedule_dump_state("planned maintenances changed")


def reschedule_dump_state(log_msg: str) -> None:
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id=STATE_DUMP_JOB_ID)
    next_run = datetime.now(tz=tzlocal.get_localzone()) + MINIMUM_STATE_DUMP_INTERVAL
    if job.next_run_time > next_run:
        _log.debug("%s, Rescheduling state dump from %s to %s", log_msg, job.next_run_time, next_run)
        job.modify(next_run_time=next_run)


async def log_snmp_session_stats():
    """Logs debug information about the current number of SNMP session objects"""
    logger = logging.getLogger("zino.snmp")
    if not logger.isEnabledFor(logging.DEBUG):
        return  # Skip potentially expensive count operations if debug logging is not enabled

    backend = import_snmp_backend()
    log_low_level = "netsnmpy" in backend.__name__

    from zino.snmp import SNMP, _snmp_sessions

    device_count = len(state.state.devices)
    reusable = len(_snmp_sessions) if _snmp_sessions else 0

    msg = "(SNMP) session update: routers=%d, reusable (zino)=%d, gc reachable (high-level)=%d"
    if log_low_level:
        from netsnmpy.session import Session

        counts = _count_reachable_objects(SNMP, Session)
        counts = counts[SNMP], counts[Session]
        msg += ", gc reachable (low-level)=%d"
    else:
        counts = _count_reachable_objects(SNMP)
        counts = (counts[SNMP],)

    logger.debug(msg, device_count, reusable, *counts)


def _count_reachable_objects(*types):
    """Returns the number of objects of the given types that are currently reachable by the garbage collector.

    Designed to do a single pass over all objects in memory, for some semblance of efficiency.
    """
    counts = defaultdict(int)
    for obj in gc.get_objects():
        for t in types:
            if isinstance(obj, t):
                counts[t] += 1
    return counts


def parse_args(arguments=None):
    parser = argparse.ArgumentParser(description="Zino is not OpenView")
    parser.add_argument(
        "--version",
        action="version",
        version=f"zino {version.__version__}",
    )
    parser.add_argument(
        "--polldevs",
        type=str,
        required=False,
        help="Path to the pollfile",
    )
    parser.add_argument(
        "--config-file",
        type=str,
        required=False,
        help="Path to zino configuration file",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Set global log level to DEBUG. Very verbose! For more fine-grained control of logging configuration, it "
        "is recommended to use the 'logging' section in the configuration file.",
    )
    parser.add_argument("--stop-in", type=int, default=None, help="Stop zino after N seconds.", metavar="N")
    parser.add_argument(
        "--trap-port",
        type=int,
        metavar="PORT",
        default=162,
        help="Which UDP port to listen for traps on.  Default value is 162.  Any value below 1024 requires root "
        "privileges.  Setting to 0 disables SNMP trap monitoring.",
    )
    parser.add_argument(
        "--user", metavar="USER", help="Switch to this user immediately after binding to privileged ports"
    )
    args = parser.parse_args(args=arguments)
    return args


if __name__ == "__main__":
    main()
