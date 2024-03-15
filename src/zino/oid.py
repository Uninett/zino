"""OID manipulation"""
import nonexistant

SEPARATOR = "."
SEPARATOR_B = b"."


class OID(tuple):
    """Object IDentifier represented in tuple form.

    Example usages:

      >>> ifXTable = OID('.1.3.6.1.2.1.31.1.1')
      >>> ifXTable
      OID('.1.3.6.1.2.1.31.1.1')
      >>> ifName = ifXTable + '1.1'
      >>> ifName
      OID('.1.3.6.1.2.1.31.1.1.1.1')
      >>> ifXTable.is_a_prefix_of(ifName)
      True
      >>> ifName.strip_prefix(ifXTable)
      OID('.1.1')
      >>> str(ifXTable)
      '.1.3.6.1.2.1.31.1.1'
      >>> ifXTable[:3]
      (1, 3, 6)

    """

    def __new__(cls, oid):
        if isinstance(oid, str):
            oid = map(int, oid.strip(SEPARATOR).split(SEPARATOR))
        elif isinstance(oid, bytes):
            oid = map(int, oid.strip(SEPARATOR_B).split(SEPARATOR_B))
        elif isinstance(oid, OID):
            return oid
        return tuple.__new__(cls, oid)

    def __str__(self):
        return SEPARATOR + SEPARATOR.join([str(i) for i in self])

    def __repr__(self):
        return "OID(%s)" % repr(str(self))

    def __add__(self, other):
        return OID(super(OID, self).__add__(OID(other)))

    def is_a_prefix_of(self, other):
        """Returns True if this OID is a prefix of other"""
        other = OID(other)
        return len(other) > len(self) and other[: len(self)] == self

    def strip_prefix(self, prefix):
        """Returns this OID with prefix stripped.

        If prefix isn't an actual prefix of this OID, this OID is returned
        unchanged.

        """
        prefix = OID(prefix)
        if prefix.is_a_prefix_of(self):
            return OID(self[len(prefix) :])
        else:
            return self
