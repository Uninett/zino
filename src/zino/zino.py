#!/usr/bin/env python3
import argparse
import asyncio
import errno
import grp
import logging
import os
import pwd
import sys
from asyncio import AbstractEventLoop
from datetime import datetime, timedelta
from typing import Optional

import tzlocal
from pydantic import ValidationError

from zino import state
from zino.api.server import ZinoServer
from zino.config import InvalidConfigurationError, read_configuration
from zino.scheduler import get_scheduler, load_and_schedule_polldevs
from zino.statemodels import Event
from zino.trapd import TrapReceiver

# ensure all our desired trap observers are loaded.  They will not be explicitly referenced here, hence the noqa tag
from zino.trapobservers import (  # noqa
    bgp_traps,
    ignored_traps,
    link_traps,
    logged_traps,
)

STATE_DUMP_JOB_ID = "zino.dump_state"
# Never try to dump state more often than this:
MINIMUM_STATE_DUMP_INTERVAL = timedelta(seconds=10)
DEFAULT_CONFIG_FILE = "zino.toml"
_log = logging.getLogger("zino")


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO if not args.debug else logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s (%(threadName)s) - %(message)s",
    )
    try:
        state.config = read_configuration(args.config_file or DEFAULT_CONFIG_FILE, args.polldevs)
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

    state.state = state.ZinoState.load_state_from_file(state.config.persistence.file) or state.ZinoState()
    init_event_loop(args)


def init_event_loop(args: argparse.Namespace, loop: Optional[AbstractEventLoop] = None):
    if not loop:
        loop = asyncio.get_event_loop()

    if args.trap_port:
        trap_receiver = TrapReceiver(port=args.trap_port, loop=loop, state=state.state)
        trap_receiver.add_community("public")
        trap_receiver.add_community("secret")
        trap_receiver.auto_subscribe_observers()

        try:
            loop.run_until_complete(trap_receiver.open())
        except PermissionError:
            _log.fatal(
                "Permission denied on UDP port %s. Use --trap-port to specify unprivileged port, or run as root",
                args.trap_port,
            )
            sys.exit(errno.EACCES)
    if args.user:
        switch_to_user(args.user)

    scheduler = get_scheduler()
    scheduler.start()

    scheduler.add_job(
        func=load_and_schedule_polldevs,
        trigger="interval",
        args=(state.config.polling.file,),
        minutes=state.config.polling.period,
        next_run_time=datetime.now(),
    )
    # Schedule state dumping as often as configured in
    # 'config.persistence.period' and reschedule whenever events are committed
    scheduler.add_job(
        func=state.state.dump_state_to_file,
        trigger="interval",
        args=(state.config.persistence.file,),
        id=STATE_DUMP_JOB_ID,
        minutes=state.config.persistence.period,
    )
    # Schedule planned maintenance
    scheduler.add_job(
        func=state.state.planned_maintenances.update_pm_states,
        trigger="interval",
        args=(state.state,),
        minutes=1,
        next_run_time=datetime.now(),
    )

    state.state.events.add_event_observer(reschedule_dump_state_on_commit)
    state.state.planned_maintenances.add_pm_observer(reschedule_dump_state_on_pm_change)

    # Schedule removing events that have been closed for a certain time
    scheduler.add_job(
        func=state.state.events.delete_expired_events,
        trigger="interval",
        minutes=30,
    )

    server = ZinoServer(loop=loop, state=state.state)
    server.serve()

    if args.stop_in:
        _log.info("Instructed to stop in %s seconds", args.stop_in)
        scheduler.add_job(func=loop.stop, trigger="date", run_date=datetime.now() + timedelta(seconds=args.stop_in))

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

    return True


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


def parse_args(arguments=None):
    parser = argparse.ArgumentParser(description="Zino is not OpenView")
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
        "--debug", action="store_true", default=False, help="Set global log level to DEBUG. Very chatty!"
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
