# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Zino 2 is a full rewrite of the original Tcl-based Zino state monitor.  This
changelog only details changes from Zino 2 on and out.

## [Unreleased]

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

### Changed

- Functions for parsing the many ways IP addresses are represented in SNMP MIBs
  have been consolidated into a single function ([#183](https://github.com/Uninett/zino/issues/183))

## [2.0.0-alpha.1] - 2024-01-26

This is the first official release of Zino 2.
