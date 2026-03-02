# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Zino 2 is a full rewrite of the original Tcl-based Zino state monitor.  This
changelog only details changes from Zino 2 on and out.

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the upcoming release can be found in <https://github.com/Uninett/zino/tree/master/changelog.d/>.

<!-- towncrier release notes start -->

## [2.4.1] - 2026-02-27

### Changed

- `zinoconv` now skips BFD session state and BFD events by default. Use `--include-bfd` to opt in.

### Fixed

- Run all scheduled jobs on the event loop instead of in worker threads, preventing concurrent modification of shared state.


## [2.4.0] - 2026-02-25

### Added

- Added Dockerfile and Docker compose to facilitate running as a container ([#492](https://github.com/Uninett/zino/issues/492))
- Added documentation on how to use docker image ([#502](https://github.com/Uninett/zino/issues/502))
- Added the `--version` option to the Zino CLI ([#521](https://github.com/Uninett/zino/issues/521))
- Added `[process]` configuration section with `user` option to specify which user to drop privileges to after binding to privileged ports. ([#522](https://github.com/Uninett/zino/issues/522))

### Fixed

- State serialization now runs in a forked child process, preventing `PanicException` from concurrent modification of state data structures during JSON serialization. ([#468](https://github.com/Uninett/zino/issues/468))
- Perform a final synchronous state dump on Zino shutdown so that state changes since the last periodic dump are not lost.


## [2.3.4] - 2025-12-03

### Fixed

- Fixed bug where all recent portstate events were incorrectly considered as transitioning from a flapping state to its actual state ([#509](https://github.com/Uninett/zino/issues/509))
- Fall back to decoding incoming server protocol messages as ISO-8859-1 if UTF-8 decoding fails


## [2.3.3] - 2025-12-01

### Fixed

- Added the last remaining missing items to the `zinoconv` state converter:
  - Event close times are now converted.
  - Flapping state data is now converted.
  - Flapping port states are now converted.
- `zinoconv` verbosity about invalid IPv6 addresses in old state has been reduced
- Use microsecond timestamps in job identifiers where it is likely that two instances of the same one-shot job may be scheduled within a single second (to avoid `ConflictingError` exceptions observed in logs)

## [2.3.2] - 2025-11-27

### Added

- Details about timed out SNMP requests are now logged as debug-level messages in the `zino.tasks` logger
- Documented how to configure Zino's logging output

### Changed

- Reduced default `max-repetitions` of SNMP GET-BULK operations from 10 to 5 to avoid spurious timeouts

### Fixed

- Allow re-entrant use of SNMP sessions (avoiding unnecessary `CancelledError` exceptions) ([#503](https://github.com/Uninett/zino/issues/503))
- Unexpected timeouts in task runs are now handled and logged without a complete (scary-looking) traceback


## [2.3.1] - 2025-11-25

### Added

- Added `scheduler.misfire_grace_time` setting to enable control over APScheduler options
- Dump list of running jobs to log when USR1 signal is received

### Changed

- Bump `netsnmp-cffi` requirement to version 0.1.4 (to avoid frozen jobs)

### Fixed

- Fixed an issue where duplicate events could exist in persisted state from older Zino versions. At Zino startup these are
  now automatically resolved, keeping only the oldest (original) event open while closing the duplicates. ([#488](https://github.com/Uninett/zino/issues/488))
- Stop modifying event `updated` timestamp on event closure. Instead, track event closure through new `closed` attribute, in order to remain consistent with Zino 1 ([#490](https://github.com/Uninett/zino/issues/490))


## [2.3.0] - 2025-11-14

### Added

- Added an SNMP agent to respond to client queries for Zino uptime (to properly enable failover mechanisms in legacy clients) ([#487](https://github.com/Uninett/zino/issues/487))


## [2.2.0] - 2025-10-21

### Added

- Added new config option to post reachability event when a new device is added to show that it was discovered by Zino

  We recommend to keep this config option set to `False` the first run after upgrading. That way the new `reachable_in_last_run` device status can be populated. After running Zino for a couple of minutes the config option can be set to `True` and after a restart Zino will inform about new devices that are discovered. ([#377](https://github.com/Uninett/zino/issues/377))

### Changed

- Make the default of `snmp.trap.require_community` an empty list

  For the netsnmp backend this means that trap messages are admitted, regardless of community.

  For the pysnmp backend to work this needs to be changed to have at least one community string in that list. Otherwise no trap messages are admitted. ([#483](https://github.com/Uninett/zino/issues/483))

### Fixed

- Stop considering closed events as duplicates of open events during closed event modification ([#481](https://github.com/Uninett/zino/issues/481))


## [2.1.1] - 2025-09-29

### Added

- Added a new `snmp.trap.require_community` config option to require specific (or to disregard) community strings in incoming traps ([#421](https://github.com/Uninett/zino/issues/421))
- Documented that the command line program `snmptrap` is needed for running parts of the development test suite

### Changed

- Remove redundant information from, and improve, log messages for BFD events ([#454](https://github.com/Uninett/zino/issues/454))
- Locked `apscheduler` version requirement to latest stable series (3.11)
- Avoid noisy logging during processing of trap messages:
  - Reduced log level from ERROR to DEBUG for messages about unresolvable trap variables
  - Reduced log level from ERROR to INFO for messages about various problems with incoming trap messages

### Fixed

- Match `watchpat`/`ignorepat` patterns against any part of interface name, not just the beginning ([#426](https://github.com/Uninett/zino/issues/426))
- Match planned maintenance regexp patterns against any part of an interface or device name, not just the beginning ([#450](https://github.com/Uninett/zino/issues/450))
- Don't crash when default `zino.toml` is not found ([#458](https://github.com/Uninett/zino/issues/458))
- Close events for removed routers on startup, as well as during runtime ([#470](https://github.com/Uninett/zino/issues/470))
- Delete old state data for devices no longer defined in `polldevs.cf` ([#471](https://github.com/Uninett/zino/issues/471))
- Ensure multiple BFD events cannot be created for the same interface
  - Ensure duplicate events cannot be created, even under race conditions  ([#474](https://github.com/Uninett/zino/pull/474))
  - Make async reverse DNS lookups *before* creating BFD events, in order to avoid potential race conditions between polling and trap reception ([#475](https://github.com/Uninett/zino/pull/475))
- Ensure month and day values in old events directory structure are padded to two digits for proper sortability
- Stop incorrectly sending further event notifications to clients for events that have been scavenged - it confuses, or even crashes the clients


## [2.1.0] - 2025-09-17

### Added

- Added new config option to suppress `portstate` event generation for newly discovered interfaces ([#257](https://github.com/Uninett/zino/issues/257))
- Document how to set up Zino with systemd ([#425](https://github.com/Uninett/zino/issues/425))
- Delete events related to routers that have been removed from `polldevs.cf` ([#427](https://github.com/Uninett/zino/issues/427))
- Finish setting up the documentation-tree: Add badge, some structure, trim down the README ([#434](https://github.com/Uninett/zino/issues/434))
- Added debug logging of trap type identification information

### Changed

- Use new `snmpversion` config field in `zino.toml` to decide which SNMP version to use (default to `v2c`) ([#397](https://github.com/Uninett/zino/issues/397))
- Default to *not* create `portstate` events for newly discovered interfaces
- Reduced log level of "unknown trap" messages
- Updated `pysnmplib` dependency to PySNMP 6.2 to ensure continued test suite success


## [2.0.2] - 2025-05-16

### Fixed

- Handle unresolvable trap variables more gracefully ([#408](https://github.com/Uninett/zino/issues/408))
- Fix broken sparsewalk routine in Net-SNMP back-end (which caused `MissingInterfaceTableData` errors) ([#411](https://github.com/Uninett/zino/issues/411))
- Ensure `secrets` file configuration option is actually used by the API protocol server ([#412](https://github.com/Uninett/zino/issues/412))
- Reduce log message level for traps of unknown origin to DEBUG ([#413](https://github.com/Uninett/zino/issues/413))
- Honor `do_bgp` option from `polldevs.cf` ([#414](https://github.com/Uninett/zino/issues/414))


## [2.0.1] - 2025-04-11

### Fixed

- Ensure error messages are printed as they should be on zino startup ([#404](https://github.com/Uninett/zino/issues/404))
- Fix state converter crashing if there is a closed event ([#406](https://github.com/Uninett/zino/issues/406))


## [2.0.0] - 2025-03-14

### Added

- Calculate downtime for BGP events ([#368](https://github.com/Uninett/zino/issues/368))
- Added debug logging of low-level SNMP session details to aid in debugging low-level OS resource management problems
- Added directory for Sphinx documentation in order to set up ReadTheDocs site and secure the name `zino` there.

### Fixed

- Added alternative C-based SNMP back-end for massive performance gains ([#383](https://github.com/Uninett/zino/issues/383))
- Log "home" address changes as `DEBUG` level information, to avoid unnecessary verbosity in VRRP setups ([#215](https://github.com/Uninett/zino/issues/215))
- Fix Zino dependencies to allow running on Python 3.12 ([#386](https://github.com/Uninett/zino/issues/386))
- Fixed unintended symbolic translations in the SNMP abstraction layer, and removed now obsolete workarounds for the problem ([#389](https://github.com/Uninett/zino/issues/389))
- Removed development tools from list of optional package runtime requirements ([#399](https://github.com/Uninett/zino/issues/399))


# ## [2.0.0-beta.2] - 2024-09-03

### Added

- Added full implementation of the `CLEARFLAP` API command ([#113](https://github.com/Uninett/zino/issues/113))
- Log warning if `secrets` file is world-readable ([#280](https://github.com/Uninett/zino/issues/280))
- Only load and parse pollfile if it has been changed since last load ([#282](https://github.com/Uninett/zino/issues/282))
- Added customized logging of multiple traps, just as in Zino 1:
  - `CISCOTRAP-MIB::reload`
  - `CISCO-CONFIG-MAN-MIB::ciscoConfigManEvent`
  - `CISCO-PIM-MIB::ciscoPimInvalidRegister`
  - `CISCO-PIM-MIB::ciscoPimInvalidJoinPrune`
  - `OSPF-TRAP-MIB::ospfIfConfigError`

  ([#319](https://github.com/Uninett/zino/issues/319))
- Added support for tracking accumulated event downtime for reachability and portstate events ([#332](https://github.com/Uninett/zino/issues/332))
- Custom logging configuration can now be applied in `zino.toml`

### Changed

- Rename/alias BGP and Juniper alarm event attributes in order to have more useful variable names in Python code, while retaining aliases that are compatible with the legacy API protocol ([#352](https://github.com/Uninett/zino/issues/352))

### Fixed

- Properly use dashes in event attribute names in the legacy API ([#281](https://github.com/Uninett/zino/issues/281))
- Use Zino 1-compatible field names for serialization of planned maintenance ([#287](https://github.com/Uninett/zino/issues/287))
- Use Zino 1 field names for serialization of BGP/BFD events ([#331](https://github.com/Uninett/zino/issues/331))
- Match against port alias instead of port description when `match_type` is `regexp` or `str` for portstate maintenance events. Still matches port description for `intf-regexp`. ([#297](https://github.com/Uninett/zino/issues/297))
- Fix BGP-related Pydantic serialization warnings ([#312](https://github.com/Uninett/zino/issues/312))
- Stop logging empty interface descriptions on first discovery ([#314](https://github.com/Uninett/zino/issues/314))
- Reschedule devices whose configuration attributes where changed in the pollfile ([#330](https://github.com/Uninett/zino/issues/330))
- Use default interval from pollfile to stagger new jobs ([#337](https://github.com/Uninett/zino/issues/337))
- When matching an event to a planned maintenance, check that event is of the correct subclass ([#344](https://github.com/Uninett/zino/issues/344))
- Avoid potential state corruption issues by saving the running state to a temporary file before overwriting the existing state file ([#364](https://github.com/Uninett/zino/issues/364))
- Properly encode timedelta values as an integer number of seconds in the legacy API


## [2.0.0-beta.1] - 2024-07-09


### Removed

- Remove test-only commands from API ([#286](https://github.com/Uninett/zino/issues/286))

### Added

- Add generic Zino config file ([#224](https://github.com/Uninett/zino/issues/224))
- Add most important SNMP trap handlers
  - Port basic link trap handling from Zino 1
  - Add port flapping detection to link trap transition handlers, in accordance with Zino 1 ([#284](https://github.com/Uninett/zino/issues/284))
  - Schedule re-verification of port states after link traps are received
  - Handle incoming Juniper BGP traps ([#291](https://github.com/Uninett/zino/issues/291))
  - Update BFD session information on incoming BFD session traps ([#305](https://github.com/Uninett/zino/issues/305))
- Add planned maintenance feature ([#61](https://github.com/Uninett/zino/issues/61))
  - Add the `PM` family of API commands to manipulate planned maintenance ([#298](https://github.com/Uninett/zino/issues/298))
  - Add framework support for API "sub-commands", to support the `PM` set of commands. ([#274](https://github.com/Uninett/zino/issues/274))
- Add `POLLRTR` API command ([#219](https://github.com/Uninett/zino/issues/219))
- Add `POLLINTF` API command ([#300](https://github.com/Uninett/zino/issues/300))
- Add a dummy `CLEARFLAP` API command in order not to crash older clients
- Add `zinoconv` program for converting state from Zino 1 to Zino 2 ([#66](https://github.com/Uninett/zino/issues/66))
- Add support for `neigh_rdns` attribute in BFD events. ([#199](https://github.com/Uninett/zino/issues/199))
- Add more tests for event deletion ([#209](https://github.com/Uninett/zino/issues/209))
- Fix log message on initial Juniper chassis alarm ([#213](https://github.com/Uninett/zino/issues/213))
- Add towncrier to automatically produce changelog ([#218](https://github.com/Uninett/zino/issues/218))
- Fully support multi-varbind SNMP-GET operations ([#303](https://github.com/Uninett/zino/issues/303))
- Add tests to show that one will not get closed events using `get_or_create_event()`
- Index recently closed events to facilitate updating of prematurely closed flapping events

### Changed

- Handle errors from changed SNMP interface in Juniper alarm task ([#212](https://github.com/Uninett/zino/issues/212))

### Fixed

- Improve error reporting, including line/block location, for `polldevs.cf` parsing errors ([#248](https://github.com/Uninett/zino/issues/248))
- Properly handle Juniper devices without SNMP values for red/yellow alarm count ([#231](https://github.com/Uninett/zino/issues/231))
- Properly handle "varbind" error values for SNMP v2 GET operations ([#261](https://github.com/Uninett/zino/issues/261))
- API now listens to all interfaces, not just loopback ([#285](https://github.com/Uninett/zino/issues/285))
- Resolve value types of incoming SNMP traps correctly ([#290](https://github.com/Uninett/zino/issues/290))
- Ensure polling single interfaces does not crash in the event of timeout errors
- Ensure polling single interfaces works for `ifindex=0`


## [2.0.0-alpha.2] - 2024-04-09

### Added

- SNMP traps can now be received, logged and ignored (although no useful
  handlers have been implemented yet)
  (([#189](https://github.com/Uninett/zino/pull/189),
  [#193](https://github.com/Uninett/zino/pull/193))
- Closed events now properly expire and are evicted from the running state
  after 8 hours ([#203](https://github.com/Uninett/zino/pull/203)).
- Expired events are dumped to separate JSON files in the `old-events/`
  directory ([#204](https://github.com/Uninett/zino/pull/204)).

### Fixed

- BGP events are now presented with correctly named attributes in the legacy
  API ([#172](https://github.com/Uninett/zino/issues/172))
- BGP task no longer crashes on unexpected SNMP responses while probing for
  which BGP MIB to use for a device ([#184](https://github.com/Uninett/zino/issues/184))
- Legacy API now correctly hides closed events ([#192](https://github.com/Uninett/zino/issues/192))
- Legacy API now correctly denies re-opening of closed events ([#201](https://github.com/Uninett/zino/issues/201))
- BFD events now have the expected `lastevent` attribute ([#200](https://github.com/Uninett/zino/issues/200))
- Fixed potential bug with how `portstate` events are indexed internally in
  Zino's running state ([#206](https://github.com/Uninett/zino/issues/206))
- API now responds with a proper message on user authentication failures
  ([#210](https://github.com/Uninett/zino/pull/210))

### Changed

- Functions for parsing the many ways IP addresses are represented in SNMP MIBs
  have been consolidated into a single function ([#183](https://github.com/Uninett/zino/issues/183))

## [2.0.0-alpha.1] - 2024-01-26

This is the first official release of Zino 2.
