# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Zino 2 is a full rewrite of the original Tcl-based Zino state monitor.  This
changelog only details changes from Zino 2 on and out.

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the upcoming release can be found in <https://github.com/Uninett/zino/tree/master/changelog.d/>.

<!-- towncrier release notes start -->

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
