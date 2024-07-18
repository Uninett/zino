#
# PySNMP MIB module CISCO-CONFIG-MAN-MIB (http://snmplabs.com/pysmi)
# ASN.1 source file:///home/mvold/d/zino/mibs/CISCO-CONFIG-MAN-MIB.my
# Produced by pysmi-0.3.4 at Thu Jul 18 11:45:22 2024
# On host agrajag platform Linux version 6.6.37 by user mvold
# Using Python version 3.11.9 (main, Apr  2 2024, 08:25:04) [GCC 13.2.0]
#
OctetString, Integer, ObjectIdentifier = mibBuilder.importSymbols("ASN1", "OctetString", "Integer", "ObjectIdentifier")
NamedValues, = mibBuilder.importSymbols("ASN1-ENUMERATION", "NamedValues")
ConstraintsUnion, ValueSizeConstraint, ValueRangeConstraint, ConstraintsIntersection, SingleValueConstraint = mibBuilder.importSymbols("ASN1-REFINEMENT", "ConstraintsUnion", "ValueSizeConstraint", "ValueRangeConstraint", "ConstraintsIntersection", "SingleValueConstraint")
ciscoMgmt, = mibBuilder.importSymbols("CISCO-SMI", "ciscoMgmt")
ModuleCompliance, NotificationGroup, ObjectGroup = mibBuilder.importSymbols("SNMPv2-CONF", "ModuleCompliance", "NotificationGroup", "ObjectGroup")
TimeTicks, Counter32, Gauge32, ObjectIdentity, Unsigned32, MibScalar, MibTable, MibTableRow, MibTableColumn, Integer32, Bits, Counter64, NotificationType, MibIdentifier, IpAddress, ModuleIdentity, iso = mibBuilder.importSymbols("SNMPv2-SMI", "TimeTicks", "Counter32", "Gauge32", "ObjectIdentity", "Unsigned32", "MibScalar", "MibTable", "MibTableRow", "MibTableColumn", "Integer32", "Bits", "Counter64", "NotificationType", "MibIdentifier", "IpAddress", "ModuleIdentity", "iso")
TextualConvention, DisplayString = mibBuilder.importSymbols("SNMPv2-TC", "TextualConvention", "DisplayString")
ciscoConfigManMIB = ModuleIdentity((1, 3, 6, 1, 4, 1, 9, 9, 43))
ciscoConfigManMIB.setRevisions(('1995-11-28 00:00',))
if mibBuilder.loadTexts: ciscoConfigManMIB.setLastUpdated('9511280000Z')
if mibBuilder.loadTexts: ciscoConfigManMIB.setOrganization('Cisco Systems, Inc.')
ciscoConfigManMIBObjects = MibIdentifier((1, 3, 6, 1, 4, 1, 9, 9, 43, 1))
ccmHistory = MibIdentifier((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1))
class HistoryEventMedium(TextualConvention, Integer32):
    status = 'current'
    subtypeSpec = Integer32.subtypeSpec + ConstraintsUnion(SingleValueConstraint(1, 2, 3, 4, 5, 6, 7))
    namedValues = NamedValues(("erase", 1), ("commandSource", 2), ("running", 3), ("startup", 4), ("local", 5), ("networkTftp", 6), ("networkRcp", 7))

ccmHistoryRunningLastChanged = MibScalar((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 1), TimeTicks()).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryRunningLastChanged.setStatus('current')
ccmHistoryRunningLastSaved = MibScalar((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 2), TimeTicks()).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryRunningLastSaved.setStatus('current')
ccmHistoryStartupLastChanged = MibScalar((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 3), TimeTicks()).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryStartupLastChanged.setStatus('current')
ccmHistoryMaxEventEntries = MibScalar((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 4), Integer32().subtype(subtypeSpec=ValueRangeConstraint(0, 2147483647))).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryMaxEventEntries.setStatus('current')
ccmHistoryEventEntriesBumped = MibScalar((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 5), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventEntriesBumped.setStatus('current')
ccmHistoryEventTable = MibTable((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6), )
if mibBuilder.loadTexts: ccmHistoryEventTable.setStatus('current')
ccmHistoryEventEntry = MibTableRow((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1), ).setIndexNames((0, "CISCO-CONFIG-MAN-MIB", "ccmHistoryEventIndex"))
if mibBuilder.loadTexts: ccmHistoryEventEntry.setStatus('current')
ccmHistoryEventIndex = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 1), Integer32().subtype(subtypeSpec=ValueRangeConstraint(1, 2147483647)))
if mibBuilder.loadTexts: ccmHistoryEventIndex.setStatus('current')
ccmHistoryEventTime = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 2), TimeTicks()).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventTime.setStatus('current')
ccmHistoryEventCommandSource = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 3), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2))).clone(namedValues=NamedValues(("commandLine", 1), ("snmp", 2)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventCommandSource.setStatus('current')
ccmHistoryEventConfigSource = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 4), HistoryEventMedium()).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventConfigSource.setStatus('current')
ccmHistoryEventConfigDestination = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 5), HistoryEventMedium()).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventConfigDestination.setStatus('current')
ccmHistoryEventTerminalType = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 6), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3, 4, 5, 6))).clone(namedValues=NamedValues(("notApplicable", 1), ("unknown", 2), ("console", 3), ("terminal", 4), ("virtual", 5), ("auxiliary", 6)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventTerminalType.setStatus('current')
ccmHistoryEventTerminalNumber = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 7), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventTerminalNumber.setStatus('current')
ccmHistoryEventTerminalUser = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 8), DisplayString().subtype(subtypeSpec=ValueSizeConstraint(0, 64))).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventTerminalUser.setStatus('current')
ccmHistoryEventTerminalLocation = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 9), DisplayString().subtype(subtypeSpec=ValueSizeConstraint(0, 64))).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventTerminalLocation.setStatus('current')
ccmHistoryEventCommandSourceAddress = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 10), IpAddress()).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventCommandSourceAddress.setStatus('current')
ccmHistoryEventVirtualHostName = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 11), DisplayString().subtype(subtypeSpec=ValueSizeConstraint(0, 64))).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventVirtualHostName.setStatus('current')
ccmHistoryEventServerAddress = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 12), IpAddress()).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventServerAddress.setStatus('current')
ccmHistoryEventFile = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 13), DisplayString().subtype(subtypeSpec=ValueSizeConstraint(0, 64))).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventFile.setStatus('current')
ccmHistoryEventRcpUser = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 9, 43, 1, 1, 6, 1, 14), DisplayString().subtype(subtypeSpec=ValueSizeConstraint(0, 64))).setMaxAccess("readonly")
if mibBuilder.loadTexts: ccmHistoryEventRcpUser.setStatus('current')
ciscoConfigManMIBNotificationPrefix = MibIdentifier((1, 3, 6, 1, 4, 1, 9, 9, 43, 2))
ciscoConfigManMIBNotifications = MibIdentifier((1, 3, 6, 1, 4, 1, 9, 9, 43, 2, 0))
ciscoConfigManEvent = NotificationType((1, 3, 6, 1, 4, 1, 9, 9, 43, 2, 0, 1)).setObjects(("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventCommandSource"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventConfigSource"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventConfigDestination"))
if mibBuilder.loadTexts: ciscoConfigManEvent.setStatus('current')
ciscoConfigManMIBConformance = MibIdentifier((1, 3, 6, 1, 4, 1, 9, 9, 43, 3))
ciscoConfigManMIBCompliances = MibIdentifier((1, 3, 6, 1, 4, 1, 9, 9, 43, 3, 1))
ciscoConfigManMIBGroups = MibIdentifier((1, 3, 6, 1, 4, 1, 9, 9, 43, 3, 2))
ciscoConfigManMIBCompliance = ModuleCompliance((1, 3, 6, 1, 4, 1, 9, 9, 43, 3, 1, 1)).setObjects(("CISCO-CONFIG-MAN-MIB", "ciscoConfigManHistoryGroup"))

if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    ciscoConfigManMIBCompliance = ciscoConfigManMIBCompliance.setStatus('current')
ciscoConfigManHistoryGroup = ObjectGroup((1, 3, 6, 1, 4, 1, 9, 9, 43, 3, 2, 1)).setObjects(("CISCO-CONFIG-MAN-MIB", "ccmHistoryRunningLastChanged"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryRunningLastSaved"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryStartupLastChanged"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryMaxEventEntries"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventEntriesBumped"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventTime"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventCommandSource"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventConfigSource"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventConfigDestination"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventTerminalType"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventTerminalNumber"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventTerminalUser"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventTerminalLocation"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventCommandSourceAddress"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventVirtualHostName"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventServerAddress"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventFile"), ("CISCO-CONFIG-MAN-MIB", "ccmHistoryEventRcpUser"))
if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    ciscoConfigManHistoryGroup = ciscoConfigManHistoryGroup.setStatus('current')
mibBuilder.exportSymbols("CISCO-CONFIG-MAN-MIB", ccmHistoryEventEntry=ccmHistoryEventEntry, ccmHistoryRunningLastSaved=ccmHistoryRunningLastSaved, HistoryEventMedium=HistoryEventMedium, ccmHistoryEventConfigDestination=ccmHistoryEventConfigDestination, ccmHistoryEventServerAddress=ccmHistoryEventServerAddress, ccmHistoryEventTerminalLocation=ccmHistoryEventTerminalLocation, ciscoConfigManMIBCompliance=ciscoConfigManMIBCompliance, ccmHistoryEventTerminalNumber=ccmHistoryEventTerminalNumber, ccmHistoryEventTerminalType=ccmHistoryEventTerminalType, ccmHistoryEventCommandSourceAddress=ccmHistoryEventCommandSourceAddress, PYSNMP_MODULE_ID=ciscoConfigManMIB, ccmHistoryEventConfigSource=ccmHistoryEventConfigSource, ccmHistoryEventFile=ccmHistoryEventFile, ciscoConfigManHistoryGroup=ciscoConfigManHistoryGroup, ccmHistoryEventVirtualHostName=ccmHistoryEventVirtualHostName, ccmHistoryStartupLastChanged=ccmHistoryStartupLastChanged, ccmHistory=ccmHistory, ciscoConfigManMIBConformance=ciscoConfigManMIBConformance, ciscoConfigManMIBNotificationPrefix=ciscoConfigManMIBNotificationPrefix, ciscoConfigManMIBGroups=ciscoConfigManMIBGroups, ciscoConfigManMIB=ciscoConfigManMIB, ciscoConfigManMIBObjects=ciscoConfigManMIBObjects, ciscoConfigManMIBNotifications=ciscoConfigManMIBNotifications, ccmHistoryEventTerminalUser=ccmHistoryEventTerminalUser, ccmHistoryEventIndex=ccmHistoryEventIndex, ccmHistoryEventEntriesBumped=ccmHistoryEventEntriesBumped, ccmHistoryEventCommandSource=ccmHistoryEventCommandSource, ccmHistoryRunningLastChanged=ccmHistoryRunningLastChanged, ccmHistoryMaxEventEntries=ccmHistoryMaxEventEntries, ccmHistoryEventRcpUser=ccmHistoryEventRcpUser, ccmHistoryEventTable=ccmHistoryEventTable, ciscoConfigManMIBCompliances=ciscoConfigManMIBCompliances, ccmHistoryEventTime=ccmHistoryEventTime, ciscoConfigManEvent=ciscoConfigManEvent)