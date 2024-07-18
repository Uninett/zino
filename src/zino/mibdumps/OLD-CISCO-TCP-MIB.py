#
# PySNMP MIB module OLD-CISCO-TCP-MIB (http://snmplabs.com/pysmi)
# ASN.1 source file:///home/mvold/mibs/cisco/OLD-CISCO-TCP-MIB.my
# Produced by pysmi-0.3.4 at Thu Jul 18 11:03:56 2024
# On host agrajag platform Linux version 6.6.37 by user mvold
# Using Python version 3.11.9 (main, Apr  2 2024, 08:25:04) [GCC 13.2.0]
#
Integer, ObjectIdentifier, OctetString = mibBuilder.importSymbols("ASN1", "Integer", "ObjectIdentifier", "OctetString")
NamedValues, = mibBuilder.importSymbols("ASN1-ENUMERATION", "NamedValues")
SingleValueConstraint, ValueSizeConstraint, ValueRangeConstraint, ConstraintsUnion, ConstraintsIntersection = mibBuilder.importSymbols("ASN1-REFINEMENT", "SingleValueConstraint", "ValueSizeConstraint", "ValueRangeConstraint", "ConstraintsUnion", "ConstraintsIntersection")
local, = mibBuilder.importSymbols("CISCO-SMI", "local")
NotificationGroup, ModuleCompliance = mibBuilder.importSymbols("SNMPv2-CONF", "NotificationGroup", "ModuleCompliance")
Bits, Counter64, IpAddress, iso, Gauge32, Integer32, ModuleIdentity, Unsigned32, MibIdentifier, ObjectIdentity, MibScalar, MibTable, MibTableRow, MibTableColumn, NotificationType, Counter32, TimeTicks = mibBuilder.importSymbols("SNMPv2-SMI", "Bits", "Counter64", "IpAddress", "iso", "Gauge32", "Integer32", "ModuleIdentity", "Unsigned32", "MibIdentifier", "ObjectIdentity", "MibScalar", "MibTable", "MibTableRow", "MibTableColumn", "NotificationType", "Counter32", "TimeTicks")
TextualConvention, DisplayString = mibBuilder.importSymbols("SNMPv2-TC", "TextualConvention", "DisplayString")
tcpConnRemPort, tcpConnLocalPort, tcpConnLocalAddress, tcpConnRemAddress = mibBuilder.importSymbols("TCP-MIB", "tcpConnRemPort", "tcpConnLocalPort", "tcpConnLocalAddress", "tcpConnRemAddress")
ltcp = MibIdentifier((1, 3, 6, 1, 4, 1, 9, 2, 6))
ltcpConnTable = MibTable((1, 3, 6, 1, 4, 1, 9, 2, 6, 1), )
if mibBuilder.loadTexts: ltcpConnTable.setStatus('deprecated')
ltcpConnEntry = MibTableRow((1, 3, 6, 1, 4, 1, 9, 2, 6, 1, 1), ).setIndexNames((0, "TCP-MIB", "tcpConnLocalAddress"), (0, "TCP-MIB", "tcpConnLocalPort"), (0, "TCP-MIB", "tcpConnRemAddress"), (0, "TCP-MIB", "tcpConnRemPort"))
if mibBuilder.loadTexts: ltcpConnEntry.setStatus('deprecated')
loctcpConnInBytes = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 6, 1, 1, 1), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: loctcpConnInBytes.setStatus('deprecated')
loctcpConnOutBytes = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 6, 1, 1, 2), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: loctcpConnOutBytes.setStatus('deprecated')
loctcpConnInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 6, 1, 1, 3), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: loctcpConnInPkts.setStatus('deprecated')
loctcpConnOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 6, 1, 1, 4), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: loctcpConnOutPkts.setStatus('deprecated')
loctcpConnElapsed = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 6, 1, 1, 5), TimeTicks()).setMaxAccess("readonly")
if mibBuilder.loadTexts: loctcpConnElapsed.setStatus('deprecated')
mibBuilder.exportSymbols("OLD-CISCO-TCP-MIB", loctcpConnOutBytes=loctcpConnOutBytes, loctcpConnOutPkts=loctcpConnOutPkts, loctcpConnInBytes=loctcpConnInBytes, loctcpConnElapsed=loctcpConnElapsed, ltcp=ltcp, ltcpConnEntry=ltcpConnEntry, loctcpConnInPkts=loctcpConnInPkts, ltcpConnTable=ltcpConnTable)
