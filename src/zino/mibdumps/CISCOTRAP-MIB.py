#
# PySNMP MIB module CISCOTRAP-MIB (http://snmplabs.com/pysmi)
# ASN.1 source file:///home/mvold/mibs/cisco/CISCOTRAP-MIB.my
# Produced by pysmi-0.3.4 at Thu Jul 18 11:46:40 2024
# On host agrajag platform Linux version 6.6.37 by user mvold
# Using Python version 3.11.9 (main, Apr  2 2024, 08:25:04) [GCC 13.2.0]
#
OctetString, ObjectIdentifier, Integer = mibBuilder.importSymbols("ASN1", "OctetString", "ObjectIdentifier", "Integer")
NamedValues, = mibBuilder.importSymbols("ASN1-ENUMERATION", "NamedValues")
SingleValueConstraint, ValueSizeConstraint, ValueRangeConstraint, ConstraintsUnion, ConstraintsIntersection = mibBuilder.importSymbols("ASN1-REFINEMENT", "SingleValueConstraint", "ValueSizeConstraint", "ValueRangeConstraint", "ConstraintsUnion", "ConstraintsIntersection")
cisco, = mibBuilder.importSymbols("CISCO-SMI", "cisco")
ifType, ifIndex, ifDescr = mibBuilder.importSymbols("IF-MIB", "ifType", "ifIndex", "ifDescr")
locIfReason, = mibBuilder.importSymbols("OLD-CISCO-INTERFACES-MIB", "locIfReason")
whyReload, authAddr = mibBuilder.importSymbols("OLD-CISCO-SYSTEM-MIB", "whyReload", "authAddr")
loctcpConnInBytes, loctcpConnOutBytes, loctcpConnElapsed = mibBuilder.importSymbols("OLD-CISCO-TCP-MIB", "loctcpConnInBytes", "loctcpConnOutBytes", "loctcpConnElapsed")
tsLineUser, tslineSesType = mibBuilder.importSymbols("OLD-CISCO-TS-MIB", "tsLineUser", "tslineSesType")
egpNeighAddr, = mibBuilder.importSymbols("RFC1213-MIB", "egpNeighAddr")
ModuleCompliance, NotificationGroup = mibBuilder.importSymbols("SNMPv2-CONF", "ModuleCompliance", "NotificationGroup")
sysUpTime, snmp = mibBuilder.importSymbols("SNMPv2-MIB", "sysUpTime", "snmp")
Counter64, Integer32, Bits, Counter32, ModuleIdentity, MibScalar, MibTable, MibTableRow, MibTableColumn, TimeTicks, iso, NotificationType, Unsigned32, IpAddress, Gauge32, ObjectIdentity, MibIdentifier, NotificationType = mibBuilder.importSymbols("SNMPv2-SMI", "Counter64", "Integer32", "Bits", "Counter32", "ModuleIdentity", "MibScalar", "MibTable", "MibTableRow", "MibTableColumn", "TimeTicks", "iso", "NotificationType", "Unsigned32", "IpAddress", "Gauge32", "ObjectIdentity", "MibIdentifier", "NotificationType")
DisplayString, TextualConvention = mibBuilder.importSymbols("SNMPv2-TC", "DisplayString", "TextualConvention")
tcpConnState, = mibBuilder.importSymbols("TCP-MIB", "tcpConnState")
coldStart = NotificationType((1, 3, 6, 1, 2, 1, 11) + (0,0)).setObjects(("SNMPv2-MIB", "sysUpTime"), ("OLD-CISCO-SYSTEM-MIB", "whyReload"))
linkDown = NotificationType((1, 3, 6, 1, 2, 1, 11) + (0,2)).setObjects(("IF-MIB", "ifIndex"), ("IF-MIB", "ifDescr"), ("IF-MIB", "ifType"), ("OLD-CISCO-INTERFACES-MIB", "locIfReason"))
linkUp = NotificationType((1, 3, 6, 1, 2, 1, 11) + (0,3)).setObjects(("IF-MIB", "ifIndex"), ("IF-MIB", "ifDescr"), ("IF-MIB", "ifType"), ("OLD-CISCO-INTERFACES-MIB", "locIfReason"))
authenticationFailure = NotificationType((1, 3, 6, 1, 2, 1, 11) + (0,4)).setObjects(("OLD-CISCO-SYSTEM-MIB", "authAddr"))
egpNeighborLoss = NotificationType((1, 3, 6, 1, 2, 1, 11) + (0,5)).setObjects(("RFC1213-MIB", "egpNeighAddr"))
reload = NotificationType((1, 3, 6, 1, 4, 1, 9) + (0,0)).setObjects(("SNMPv2-MIB", "sysUpTime"), ("OLD-CISCO-SYSTEM-MIB", "whyReload"))
tcpConnectionClose = NotificationType((1, 3, 6, 1, 4, 1, 9) + (0,1)).setObjects(("OLD-CISCO-TS-MIB", "tslineSesType"), ("TCP-MIB", "tcpConnState"), ("OLD-CISCO-TCP-MIB", "loctcpConnElapsed"), ("OLD-CISCO-TCP-MIB", "loctcpConnInBytes"), ("OLD-CISCO-TCP-MIB", "loctcpConnOutBytes"), ("OLD-CISCO-TS-MIB", "tsLineUser"))
mibBuilder.exportSymbols("CISCOTRAP-MIB", linkUp=linkUp, reload=reload, tcpConnectionClose=tcpConnectionClose, egpNeighborLoss=egpNeighborLoss, coldStart=coldStart, authenticationFailure=authenticationFailure, linkDown=linkDown)
