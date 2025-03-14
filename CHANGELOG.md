# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Zino 2 is a full rewrite of the original Tcl-based Zino state monitor.  This
changelog only details changes from Zino 2 on and out.

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the upcoming release can be found in <https://github.com/Uninett/zino/tree/master/changelog.d/>.

<!-- towncrier release notes start -->

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
