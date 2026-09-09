What is Zino?
=============

**Zino Is Not OpenView.**

That recursive acronym, a reference to HP OpenView (a dominant commercial network
management platform of the 1990s), captures both Zino's origin and its
philosophy: a lightweight, focused alternative to heavyweight enterprise
solutions. The self-referential name follows a tradition beloved by Unix
hackers, in the spirit of GNU ("GNU's Not Unix").

Origin and History
------------------

Zino was created in 1996 at `Uninett <https://www.uninett.no/>`_, the
organization that operates the Norwegian national research and education
network (NREN). The initiator and driving force behind Zino was Håvard Eidnes,
who needed a practical tool to monitor the routers of a large backbone network
connecting Norway's geographically dispersed universities and research
institutions.

The original implementation was written in Tcl using the Scotty extension
(which provided SNMP capabilities), comprising approximately 5,000 lines of
code. Despite its modest size, Zino proved remarkably effective and
battle-tested over decades of production use.

Adoption beyond Norway came in 1999 when SUNET (the Swedish NREN) began using
Zino at their Network Operations Center. NORDUnet, the collaboration that
interconnects the Nordic NRENs, also adopted Zino for monitoring its backbone.
Today, Zino is used by Uninett (now Sikt), NORDUnet, SUNET, and RHNet (the
Icelandic NREN).

The Python Rewrite
------------------

After nearly three decades of service, the original Tcl codebase faced
challenges: the Tcl/Scotty ecosystem had become obscure, making maintenance
difficult and onboarding new developers nearly impossible. In response,
NORDUnet sponsored a complete rewrite in Python, with the goal that all Nordic
NRENs would use the modernized version.

This project (Zino 2) preserves the original's design philosophy and maintains
backwards compatibility with the legacy client/server protocol, allowing
existing tools like *Ritz* and *curitz* to continue working unchanged.

The Problem Zino Solves
-----------------------

Zino occupies a specific niche in network monitoring: **state change tracking
for backbone networks**.

Unlike metric-focused systems (Prometheus, Graphite) that collect and graph
time-series data, or availability monitors (Nagios, Icinga) that check whether
services respond, Zino tracks *state transitions* in network infrastructure:

- A router is unreachable (or reachable again)
- A link goes down (or comes back up)
- A BGP session drops (or re-establishes)
- A BFD session fails
- A Juniper router raises a chassis alarm

Each state change creates an **event** (also called a **case**) that persists
until a human operator explicitly closes it. This human-in-the-loop design is
intentional: backbone network issues often require investigation, coordination,
and documentation before they can be considered resolved.

Design Philosophy
-----------------

Several principles guide Zino's design:

**Event-driven, not metric-driven**
    Zino doesn't collect throughput statistics or graph bandwidth utilization.
    It watches for state changes and creates cases that need attention. If you
    want traffic graphs, use a complementary tool.

**Human-in-the-loop**
    Events don't auto-close when a link recovers. An operator must acknowledge
    or comment and close each case. This is a deliberate policy choice in
    support of normal NOC practice: auto-closing would hide problems that are
    operationally up again but whose root cause was never found, and finding
    and eliminating root causes is the point. Manual closure also leaves an
    audit trail of network incidents.

**Trap-directed polling**
    Zino uses a hybrid approach: it listens for SNMP traps (immediate
    notifications from devices) but also performs periodic polling. Traps
    provide fast notification; polling provides confirmation and catches
    issues where traps were lost or never sent. This "trust but verify"
    model improves reliability.

**Minimal footprint**
    The original fit in about 5,000 lines of Tcl. The Python rewrite is
    about 5,100 lines as of this writing. Zino 2 has few dependencies, runs as
    a single process, and stores state in a simple JSON file. No database
    server required.


**Client/server architecture**
    Zino, by design, features *no* GUI: It is purely a back-end
    monitor. Instead, Zino provides a simple, SMTP-like protocol for clients
    to interact with the server. Zino 2 preserves the Zino 1 protocol, so
    that existing user interfaces and integrations can continue to work.

Zino user interfaces
--------------------

* **curitz** - a curses/terminal-based remote interface to Zino. Curitz is
  implemented in Python and is easy to install and use. See the `curitz GitHub
  repository for more information <https://github.com/Uninett/curitz/>`_.
* **Argus** - a web based interface. `Argus is a general purpose incident
  management tool <https://network.geant.org/argus/>`_ that can be integrated
  with many monitoring tools.  A `two-way zino-argus integration is available
  <https://github.com/Uninett/zino-argus-glue/>`_.
* **Ritz** - the original, X11-based *Remote Interface To Zino*, implemented in
  Tcl. The Ritz client is part of the original Zino 1 codebase, which is
  currently only available as `a tarball at the NORDUnet FTP site
  <https://ftp.nordu.net/nordunet/NORDstat/zino-1.0.tar.gz>`_.

How Zino Fits In
----------------

A typical NREN monitoring stack might include:

- **Traffic statistics**: Tools like nfsen, LibreNMS, or similar for bandwidth
  and flow analysis
- **Availability monitoring**: Nagios, Icinga, or similar for service checks
- **Zino**: For router state monitoring and incident case management

Zino complements rather than replaces these tools. Its strength is providing a
focused, reliable view of backbone router health with a workflow designed for
NOC operations.

Acknowledgments
---------------

Zino exists thanks to:

- **Håvard Eidnes**, creator and long-time maintainer of the original Tcl
  implementation
- **Uninett** (now Sikt), where Zino was born
- **NORDUnet**, sponsor of the Python rewrite
- The NOC teams at the Nordic NRENs who have used and refined Zino over three
  decades
