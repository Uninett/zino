
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
