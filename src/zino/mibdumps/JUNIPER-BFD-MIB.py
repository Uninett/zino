#
# PySNMP MIB module JUNIPER-BFD-MIB (http://snmplabs.com/pysmi)
# ASN.1 source file://./JUNIPER-BFD-MIB.mib
# Produced by pysmi-1.1.10 at Mon Oct  9 12:14:08 2023
# On host simtve-ThinkPad-X1-Carbon-Gen-9 platform Linux version 5.15.0-84-generic by user simon
# Using Python version 3.9.18 (main, Aug 25 2023, 13:20:04) 
#
Integer, ObjectIdentifier, OctetString = mibBuilder.importSymbols("ASN1", "Integer", "ObjectIdentifier", "OctetString")
NamedValues, = mibBuilder.importSymbols("ASN1-ENUMERATION", "NamedValues")
ConstraintsUnion, ValueRangeConstraint, ValueSizeConstraint, ConstraintsIntersection, SingleValueConstraint = mibBuilder.importSymbols("ASN1-REFINEMENT", "ConstraintsUnion", "ValueRangeConstraint", "ValueSizeConstraint", "ConstraintsIntersection", "SingleValueConstraint")
bfdSessIndex, = mibBuilder.importSymbols("BFD-STD-MIB", "bfdSessIndex")
jnxBfdMibRoot, = mibBuilder.importSymbols("JUNIPER-SMI", "jnxBfdMibRoot")
NotificationGroup, ModuleCompliance = mibBuilder.importSymbols("SNMPv2-CONF", "NotificationGroup", "ModuleCompliance")
IpAddress, ModuleIdentity, Bits, MibIdentifier, Counter64, iso, Integer32, TimeTicks, NotificationType, Unsigned32, MibScalar, MibTable, MibTableRow, MibTableColumn, ObjectIdentity, Gauge32, Counter32 = mibBuilder.importSymbols("SNMPv2-SMI", "IpAddress", "ModuleIdentity", "Bits", "MibIdentifier", "Counter64", "iso", "Integer32", "TimeTicks", "NotificationType", "Unsigned32", "MibScalar", "MibTable", "MibTableRow", "MibTableColumn", "ObjectIdentity", "Gauge32", "Counter32")
TimeStamp, DisplayString, TruthValue, TextualConvention = mibBuilder.importSymbols("SNMPv2-TC", "TimeStamp", "DisplayString", "TruthValue", "TextualConvention")
jnxBfdMib = ModuleIdentity((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1))
jnxBfdMib.setRevisions(('2006-10-12 12:00',))

if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    if mibBuilder.loadTexts: jnxBfdMib.setRevisionsDescriptions(('Initial version.',))
if mibBuilder.loadTexts: jnxBfdMib.setLastUpdated('200610121200Z')
if mibBuilder.loadTexts: jnxBfdMib.setOrganization('IETF')
if mibBuilder.loadTexts: jnxBfdMib.setContactInfo(' Juniper Technical Assistance Center Juniper Networks, Inc. 1194 N. Mathilda Avenue Sunnyvale, CA 94089 E-mail: support@juniper.net')
if mibBuilder.loadTexts: jnxBfdMib.setDescription('Provides BFD specific data.')
jnxBfdNotification = MibIdentifier((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 0))
jnxBfdObjects = MibIdentifier((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 1))
jnxBfdNotifyObjects = MibIdentifier((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 2))
jnxBfdSessTable = MibTable((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 1, 1), )
if mibBuilder.loadTexts: jnxBfdSessTable.setStatus('current')
if mibBuilder.loadTexts: jnxBfdSessTable.setDescription('Defines the jnxBfd Session Table for providing enterprise specific options to the corresponding bfdSessTable entry.')
jnxBfdSessEntry = MibTableRow((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 1, 1, 1), ).setIndexNames((0, "BFD-STD-MIB", "bfdSessIndex"))
if mibBuilder.loadTexts: jnxBfdSessEntry.setStatus('current')
if mibBuilder.loadTexts: jnxBfdSessEntry.setDescription('Defines an entry in the jnxBfdSessTable. This essentially augments the bfdSessTable with additional objects.')
jnxBfdSessThreshTxInterval = MibTableColumn((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 1, 1, 1, 1), Unsigned32()).setUnits('microseconds').setMaxAccess("readonly")
if mibBuilder.loadTexts: jnxBfdSessThreshTxInterval.setStatus('current')
if mibBuilder.loadTexts: jnxBfdSessThreshTxInterval.setDescription('The threshold value for transmit interval in microseconds. If the current transmit interval value adapts to a value greater than the threshold value, jnxBfdSessTxIntervalHigh trap is raised.')
jnxBfdSessCurrTxInterval = MibTableColumn((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 1, 1, 1, 2), Unsigned32()).setUnits('microseconds').setMaxAccess("readonly")
if mibBuilder.loadTexts: jnxBfdSessCurrTxInterval.setStatus('current')
if mibBuilder.loadTexts: jnxBfdSessCurrTxInterval.setDescription('The current transmit interval in microseconds.')
jnxBfdSessThreshDectTime = MibTableColumn((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 1, 1, 1, 3), Unsigned32()).setUnits('microseconds').setMaxAccess("readonly")
if mibBuilder.loadTexts: jnxBfdSessThreshDectTime.setStatus('current')
if mibBuilder.loadTexts: jnxBfdSessThreshDectTime.setDescription('The threshold value for detection time in microseconds. If the current detection time value is greater than the threshold value at the time when session state changes to up(1), jnxBfdSessDetectionTimeHigh trap is raised.')
jnxBfdSessCurrDectTime = MibTableColumn((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 1, 1, 1, 4), Unsigned32()).setUnits('microseconds').setMaxAccess("readonly")
if mibBuilder.loadTexts: jnxBfdSessCurrDectTime.setStatus('current')
if mibBuilder.loadTexts: jnxBfdSessCurrDectTime.setDescription('The actual value of detection time for the session.')
jnxBfdSessIntfName = MibTableColumn((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 1, 1, 1, 5), DisplayString()).setMaxAccess("readonly")
if mibBuilder.loadTexts: jnxBfdSessIntfName.setStatus('current')
if mibBuilder.loadTexts: jnxBfdSessIntfName.setDescription('This object specifies the interface associated with the bfd session')
jnxBfdSessifName = MibScalar((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 2, 1), DisplayString()).setMaxAccess("accessiblefornotify")
if mibBuilder.loadTexts: jnxBfdSessifName.setStatus('current')
if mibBuilder.loadTexts: jnxBfdSessifName.setDescription('This object gives the Interface Name in the bfdSessUp and bfdSessDown trap. Even though this object doesnt appear in the OBJECTS list of these traps, but the agent relay this information as an extra parameter in the trap.')
jnxBfdSessTxIntervalHigh = NotificationType((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 0, 1)).setObjects(("JUNIPER-BFD-MIB", "jnxBfdSessThreshTxInterval"), ("JUNIPER-BFD-MIB", "jnxBfdSessCurrTxInterval"))
if mibBuilder.loadTexts: jnxBfdSessTxIntervalHigh.setStatus('current')
if mibBuilder.loadTexts: jnxBfdSessTxIntervalHigh.setDescription('This notification is generated when the threshold value for transmit interval (jnxBfdSessThreshTxInterval) is set and the bfd session transmit interval (jnxBfdSessCurrTxInterval) adapts to a value greater than the threshold value. This trap is sent only once, when we first exceed the threshold. The transmit interval can continue to adapt beyond the threshold value. Adaptation of transmit interval happens due to network issues causing the BFD session to go down on either the local system or the remote neighbor.')
jnxBfdSessDetectionTimeHigh = NotificationType((1, 3, 6, 1, 4, 1, 2636, 3, 45, 1, 0, 2)).setObjects(("JUNIPER-BFD-MIB", "jnxBfdSessThreshDectTime"), ("JUNIPER-BFD-MIB", "jnxBfdSessCurrDectTime"))
if mibBuilder.loadTexts: jnxBfdSessDetectionTimeHigh.setStatus('current')
if mibBuilder.loadTexts: jnxBfdSessDetectionTimeHigh.setDescription('This notification is generated when the threshold value for detection time (jnxBfdSessThreshDectTime) is set and the bfd session detection-time (jnxBfdSessCurrDectTime) adapts to a value greater than the threshold value. This trap is sent only once, when we first exceed the threshold. The detection-time can continue to adapt beyond the threshold value. Adaptation of detection-time happens due to network issues causing the BFD session to go down on either the local system or the remote neighbor.')
mibBuilder.exportSymbols("JUNIPER-BFD-MIB", jnxBfdSessIntfName=jnxBfdSessIntfName, jnxBfdSessThreshTxInterval=jnxBfdSessThreshTxInterval, jnxBfdSessTable=jnxBfdSessTable, jnxBfdMib=jnxBfdMib, jnxBfdSessThreshDectTime=jnxBfdSessThreshDectTime, jnxBfdObjects=jnxBfdObjects, jnxBfdSessifName=jnxBfdSessifName, jnxBfdSessTxIntervalHigh=jnxBfdSessTxIntervalHigh, jnxBfdNotification=jnxBfdNotification, jnxBfdSessDetectionTimeHigh=jnxBfdSessDetectionTimeHigh, jnxBfdSessEntry=jnxBfdSessEntry, PYSNMP_MODULE_ID=jnxBfdMib, jnxBfdSessCurrDectTime=jnxBfdSessCurrDectTime, jnxBfdSessCurrTxInterval=jnxBfdSessCurrTxInterval, jnxBfdNotifyObjects=jnxBfdNotifyObjects)
