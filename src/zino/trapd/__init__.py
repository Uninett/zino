"""Zino SNMP trap daemon back-ends"""

# This is where we switch between back-ends, for now
# from zino.trapd.pysnmp_backend import *  # noqa

from zino.trapd.netsnmpy_backend import *  # noqa
