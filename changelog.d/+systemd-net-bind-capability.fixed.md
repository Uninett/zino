Reworked the systemd howto to bind the privileged SNMP trap port via the `CAP_NET_BIND_SERVICE` capability, so Zino runs as an unprivileged user instead of starting as root
