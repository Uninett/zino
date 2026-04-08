Core Concepts
=============

Understanding Zino requires familiarity with a few central concepts. This
document explains the mental model behind the system.

Events (Cases)
--------------

The **event** is Zino's fundamental abstraction. When something noteworthy
happens on the network—a link goes down, a BGP session drops, a router becomes
unreachable—Zino creates an event to track it.

Events are sometimes called **cases** (the terms are interchangeable). This
terminology reflects their purpose: each event represents a case that needs
attention, investigation, and eventual resolution by a human operator.

An event is uniquely identified by:

- **Router**: The device where the issue occurred
- **Subindex**: What specifically is affected (e.g., an interface index, a BGP
  peer address, an alarm type)
- **Type**: The kind of event (portstate, BGP, BFD, alarm, reachability)

This combination ensures that if the same link flaps repeatedly, Zino updates
the existing event rather than creating duplicates.

Event Types
-----------

Zino monitors several categories of network state:

**Port State Events** (``portstate``)
    Track interface/link status changes. Created when a link goes down or
    enters an unexpected state. The subindex is the interface's ifIndex.

**BGP Events** (``bgp``)
    Track BGP peer session state. Created when a BGP session leaves the
    ``established`` state. The subindex is the peer's IP address.

**BFD Events** (``bfd``)
    Track Bidirectional Forwarding Detection sessions. Created when BFD
    detects a forwarding path failure. The subindex is the session
    discriminator.

**Alarm Events** (``alarm``)
    Track Juniper chassis alarms (yellow and red). Created when a router
    reports hardware alarms. The subindex is the alarm type.

**Reachability Events** (``reachability``)
    Track whether Zino can reach a router at all. Created when SNMP polling
    fails repeatedly. No subindex (the whole device is affected).

Event Lifecycle
---------------

Events progress through a defined set of states:

.. mermaid::

   stateDiagram-v2
       [*] --> EMBRYONIC: new event created
       EMBRYONIC --> OPEN: committed

       OPEN --> WORKING: operator claims
       OPEN --> WAITING: operator defers
       OPEN --> IGNORED: operator ignores

       WORKING --> WAITING: waiting on external
       WORKING --> CONFIRM: condition cleared
       WAITING --> WORKING: resuming work
       WAITING --> CONFIRM: condition cleared

       CONFIRM --> CLOSED: operator confirms
       WORKING --> CLOSED: operator closes
       WAITING --> CLOSED: operator closes

       CLOSED --> [*]

       note right of OPEN: Awaiting operator attention
       note right of IGNORED: Acknowledged but not addressed

**EMBRYONIC**
    A newly created event that hasn't been committed yet. Internal state only.

**OPEN**
    The default state for new events. Indicates the issue needs attention.

**WORKING**
    An operator has claimed this event and is actively investigating.

**WAITING**
    The operator is waiting for something (vendor response, scheduled
    maintenance window, etc.).

**CONFIRM-WAIT**
    Used when the underlying condition has cleared but the operator wants to
    confirm stability before closing.

**IGNORED**
    The event is acknowledged but intentionally not being addressed (e.g.,
    known issue, decommissioned equipment).

**CLOSED**
    The event is resolved. Closed events are archived and eventually removed
    from active state.

Events accumulate a **history log** as they progress, recording state changes,
operator comments, and related network events.

Devices
-------

A **device** (or router) is any SNMP-managed network equipment that Zino
monitors. Devices are defined in the ``polldevs.cf`` configuration file, which
specifies:

- Device name (typically the DNS hostname)
- SNMP community string
- Polling interval

Zino maintains **device state** for each router, tracking:

- Known interfaces and their current states
- BGP peer sessions
- Chassis alarms (Juniper)
- Whether the device was reachable in the last polling cycle

This cached state allows Zino to detect *changes* rather than just current
conditions.

Polling and Traps
-----------------

Zino uses a **trap-directed polling** model:

**SNMP Traps** (push)
    Devices send unsolicited notifications when state changes occur. Traps
    provide immediate notification but can be lost (UDP) or may not be
    configured for all events.

**SNMP Polling** (pull)
    Zino periodically queries each device for its current state. Polling is
    slower but reliable—it catches issues even if traps were never sent.

The combination provides both speed and reliability:

1. A trap arrives indicating a link went down
2. Zino immediately polls the device to confirm
3. If confirmed, an event is created or updated
4. Periodic polling continues, catching any state changes that didn't generate
   traps

Planned Maintenance
-------------------

**Planned Maintenance** (PM) windows allow operators to suppress event creation
during scheduled work. When a PM is active for a device or pattern:

- State changes are still detected and logged
- But new events may be suppressed or automatically marked as related to
  maintenance
- This prevents the NOC from being flooded with alerts during known work

PMs are defined with:

- Start and end times
- Device name or pattern (glob matching)
- Description of the maintenance activity

Flapping Detection
------------------

A link that bounces up and down repeatedly is **flapping**. Flapping can
generate excessive events and masks the real problem.

Zino detects flapping by tracking state change frequency. When a port exceeds a
threshold of transitions within a time window, Zino:

1. Marks the port as ``flapping``
2. Stops creating new events for each individual transition
3. Creates or updates a single event noting the flapping condition

When the port stabilizes (stays in one state long enough), the flapping
designation is cleared.

Notifications
-------------

Zino provides two API ports:

**Port 8001 (Command Interface)**
    The main API for querying and manipulating events. Clients connect here to
    list events, get details, update states, and add comments.

**Port 8002 (Notification Interface)**
    A push notification channel. Clients connect and receive real-time updates
    when events are created or modified. This allows UIs to update immediately
    rather than polling.

The notification model means clients can maintain a live view of network state
without constant API queries.

State Persistence
-----------------

Zino serializes its entire state to a JSON file (``zino-state.json`` by
default) periodically and on shutdown. This includes:

- All active events
- Device state cache
- Planned maintenance windows
- Flapping state

On startup, Zino loads this file and resumes where it left off. This means:

- Events survive restarts
- Recent state changes aren't lost
- Zino can pick up monitoring without a full re-poll of all devices

The state file also enables a simple redundancy model: a standby Zino server
can periodically receive the state file from the primary and be ready to take
over if needed.
