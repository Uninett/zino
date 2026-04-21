Technical Architecture
======================

This document describes how Zino is structured internally. Understanding the
architecture helps when debugging issues, extending functionality, or
integrating with other systems.

High-Level Overview
-------------------

.. mermaid::

   flowchart TB
       subgraph Routers["Routers (SNMP devices)"]
       end

       Routers --> Traps["SNMP Traps<br/>(trapd)"]
       Routers --> Polling["SNMP Polling<br/>(tasks)"]
       Routers -.->|state queries| State

       Traps --> State["ZinoState<br/>(events, devices)"]
       Polling --> State

       State --> Port8001["Port 8001<br/>(command)"]
       State --> Port8002["Port 8002<br/>(notify)"]
       State --> StateFile["State File<br/>(JSON)"]

       Port8001 --> Clients["Client UIs<br/>(curitz, ritz, etc.)"]
       Port8002 --> Clients

Components
----------

Entry Point
^^^^^^^^^^^

The main entry point is ``zino.zino:main()``, invoked by the ``zino`` console
script. On startup, it:

1. Parses command-line arguments
2. Loads configuration (``zino.toml``, if present)
3. Initializes the SNMP backend
4. Loads persisted state from the JSON file
5. Starts the async event loop
6. Schedules polling tasks for all configured devices
7. Starts the API server and trap listener

State Management
^^^^^^^^^^^^^^^^

``ZinoState`` (in ``zino.state``) is the central container for all runtime
data:

- **devices**: Cached state for each monitored router
- **events**: All active and recently-closed events
- **addresses**: IP-to-hostname reverse mapping
- **planned_maintenances**: Active maintenance windows
- **flapping**: Flap detection state per interface

State is persisted to a JSON file periodically (default: every 5 minutes) and
on shutdown. The file format is a direct JSON serialization of the Pydantic
models.

Task System
^^^^^^^^^^^

Polling is implemented through **tasks**—async functions scheduled to run
periodically for each device. The base class ``Task`` (in ``zino.tasks.task``)
provides common functionality; concrete tasks implement the ``run()`` method.

**ReachableTask**
    Checks basic SNMP connectivity. If a device becomes unreachable, creates a
    reachability event. This runs first to avoid pointless polling of
    unreachable devices.

**LinkStateTask**
    Polls interface table (IF-MIB) to detect link state changes. Compares
    current state against cached state to identify transitions.

**BGPStateMonitorTask**
    Polls BGP peer tables to detect session state changes. Supports multiple
    BGP styles (Juniper, Cisco, generic MIBs).

**BFDTask**
    Polls BFD session state. BFD provides sub-second failure detection, and
    Zino tracks when sessions leave the "up" state.

**JuniperAlarmTask**
    Polls Juniper-specific chassis alarm MIBs. Only runs on devices identified
    as Juniper equipment.

Tasks are scheduled using APScheduler, with intervals defined per-device in
``polldevs.cf``.

SNMP Subsystem
^^^^^^^^^^^^^^

Zino supports two SNMP backends:

**Net-SNMP** (default)
    Uses the ``netsnmp`` Python bindings to the Net-SNMP C library. Faster and
    more mature, but requires system libraries to be installed.

**PySNMP**
    Pure Python implementation. Easier to install (pip only) but somewhat
    slower. Useful when Net-SNMP isn't available.

The backend is selected via configuration and abstracted behind a common
interface (``zino.snmp``), so tasks don't need to know which backend is in use.

Trap Handling
^^^^^^^^^^^^^

The trap daemon (``zino.trapd``) listens for incoming SNMP traps on a
configured port (default: 162, or 1162 for non-root operation).

When a trap arrives, it's dispatched to **trap observers**—handler functions
registered for specific trap types:

- ``link_traps``: Handles linkUp/linkDown notifications
- ``bgp_traps``: Handles BGP state change traps
- ``bfd_traps``: Handles BFD session traps
- ``logged_traps``: Logs traps for debugging
- ``ignored_traps``: Explicitly ignores known-noisy traps

Trap observers typically trigger immediate polling to confirm the reported
state change before creating or updating events.

API Server
^^^^^^^^^^

The API server (``zino.api``) provides two TCP interfaces:

**Command Interface (port 8001)**
    Implements the legacy Zino protocol—a text-based, SMTP-like protocol where
    clients send commands and receive responses. Commands include:

    - ``CASEIDS``: List all event IDs
    - ``GETATTRS <id>``: Get event attributes
    - ``SETSTATE <id> <state>``: Change event state
    - ``ADDHIST <id>``: Add history entry
    - ``PM ADD/LIST/CANCEL``: Manage planned maintenance

    This protocol is preserved exactly from Zino 1 for backwards compatibility
    with existing clients.

**Notification Interface (port 8002)**
    A simpler protocol for push notifications. Clients connect and authenticate,
    then receive messages whenever events are created or modified. Message
    format:

    .. code-block:: text

        %%<id> <state> <type>

    Clients use this to maintain live views without polling.

Authentication
^^^^^^^^^^^^^^

Both API ports require authentication. Credentials are stored in a ``secrets``
file (configurable path), one username/password pair per line.

The authentication protocol supports both simple password and challenge-response
mechanisms, preventing password replay attacks.

Event System
^^^^^^^^^^^^

The ``Events`` container (``zino.events``) manages the event lifecycle:

- **Creating events**: Tasks call ``get_or_create_event()`` when detecting a
  state change. If an event already exists for that (router, subindex, type)
  tuple, it's returned; otherwise, a new one is created.

- **Updating events**: Events are "checked out" for modification, then
  "committed" back. This pattern allows atomic updates.

- **Observers**: Components can register as event observers to be notified when
  events change. The notification API uses this to push updates to clients.

- **Archiving**: Closed events are eventually archived to the ``old-events/``
  directory and removed from active state.

Data Flow Example
-----------------

Here's how a typical link-down scenario flows through the system:

1. **Trap arrives**: Router sends linkDown trap to port 162
2. **Trap dispatch**: ``link_traps`` observer receives the trap
3. **Immediate poll**: Observer triggers a poll of the affected interface
4. **State comparison**: ``LinkStateTask`` compares new state against cache
5. **Event creation**: Task calls ``get_or_create_event()`` for a portstate
   event
6. **Event committed**: New event is added to ``ZinoState.events``
7. **Observer notification**: Event observers are called
8. **Client notification**: Notification server pushes update to connected
   clients
9. **State persistence**: Next periodic dump saves the new event to JSON

Configuration Files
-------------------

**polldevs.cf**
    Required. Lists devices to monitor with their SNMP credentials and polling
    intervals. Zino watches this file for changes and reloads automatically.

**zino.toml**
    Optional. Configures persistence paths, logging, SNMP backend selection,
    and other operational parameters.

**secrets**
    Required for API access. Contains username/password pairs for client
    authentication.

Concurrency Model
-----------------

Zino uses Python's ``asyncio`` for concurrency:

- Polling tasks run as coroutines, allowing many devices to be polled
  concurrently without threads
- The API server handles multiple client connections concurrently
- SNMP operations are async (with appropriate backend support)

APScheduler manages task timing, triggering coroutines at configured intervals.
The scheduler runs in the same event loop as the API server and trap listener.

Extending Zino
--------------

**Adding a new task type**
    Create a new class inheriting from ``Task``, implement the ``run()`` method,
    and register it in the scheduler setup.

**Adding a new trap observer**
    Create a module in ``zino/trapobservers/``, define handler functions with
    appropriate decorators, and import the module in ``zino.py``.

**Adding new event types**
    Define a new event class in ``zino.statemodels`` inheriting from ``Event``,
    add it to the type union in ``Events``, and create corresponding tasks or
    trap observers.
