Fix a bug where a failed SNMP session open (e.g. due to file descriptor
exhaustion) could permanently wedge that device's session lock, silently
disabling closure of a concurrently-opened, shared session for the same
device and leaking a file descriptor.
