#
# PySNMP MIB module OLD-CISCO-INTERFACES-MIB (http://snmplabs.com/pysmi)
# ASN.1 source file:///home/mvold/mibs/cisco/OLD-CISCO-INTERFACES-MIB.my
# Produced by pysmi-0.3.4 at Thu Jul 18 11:03:56 2024
# On host agrajag platform Linux version 6.6.37 by user mvold
# Using Python version 3.11.9 (main, Apr  2 2024, 08:25:04) [GCC 13.2.0]
#
Integer, ObjectIdentifier, OctetString = mibBuilder.importSymbols("ASN1", "Integer", "ObjectIdentifier", "OctetString")
NamedValues, = mibBuilder.importSymbols("ASN1-ENUMERATION", "NamedValues")
SingleValueConstraint, ValueSizeConstraint, ValueRangeConstraint, ConstraintsUnion, ConstraintsIntersection = mibBuilder.importSymbols("ASN1-REFINEMENT", "SingleValueConstraint", "ValueSizeConstraint", "ValueRangeConstraint", "ConstraintsUnion", "ConstraintsIntersection")
local, = mibBuilder.importSymbols("CISCO-SMI", "local")
ifIndex, = mibBuilder.importSymbols("IF-MIB", "ifIndex")
NotificationGroup, ModuleCompliance = mibBuilder.importSymbols("SNMPv2-CONF", "NotificationGroup", "ModuleCompliance")
Bits, Counter64, IpAddress, iso, Gauge32, Integer32, ModuleIdentity, Unsigned32, MibIdentifier, ObjectIdentity, MibScalar, MibTable, MibTableRow, MibTableColumn, NotificationType, Counter32, TimeTicks = mibBuilder.importSymbols("SNMPv2-SMI", "Bits", "Counter64", "IpAddress", "iso", "Gauge32", "Integer32", "ModuleIdentity", "Unsigned32", "MibIdentifier", "ObjectIdentity", "MibScalar", "MibTable", "MibTableRow", "MibTableColumn", "NotificationType", "Counter32", "TimeTicks")
TextualConvention, DisplayString = mibBuilder.importSymbols("SNMPv2-TC", "TextualConvention", "DisplayString")
linterfaces = MibIdentifier((1, 3, 6, 1, 4, 1, 9, 2, 2))
lifTable = MibTable((1, 3, 6, 1, 4, 1, 9, 2, 2, 1), )
if mibBuilder.loadTexts: lifTable.setStatus('mandatory')
lifEntry = MibTableRow((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1), ).setIndexNames((0, "IF-MIB", "ifIndex"))
if mibBuilder.loadTexts: lifEntry.setStatus('mandatory')
locIfHardType = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 1), DisplayString()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfHardType.setStatus('mandatory')
locIfLineProt = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 2), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfLineProt.setStatus('mandatory')
locIfLastIn = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 3), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfLastIn.setStatus('mandatory')
locIfLastOut = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 4), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfLastOut.setStatus('mandatory')
locIfLastOutHang = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 5), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfLastOutHang.setStatus('mandatory')
locIfInBitsSec = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 6), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfInBitsSec.setStatus('mandatory')
locIfInPktsSec = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 7), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfInPktsSec.setStatus('mandatory')
locIfOutBitsSec = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 8), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfOutBitsSec.setStatus('mandatory')
locIfOutPktsSec = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 9), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfOutPktsSec.setStatus('mandatory')
locIfInRunts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 10), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfInRunts.setStatus('mandatory')
locIfInGiants = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 11), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfInGiants.setStatus('mandatory')
locIfInCRC = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 12), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfInCRC.setStatus('mandatory')
locIfInFrame = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 13), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfInFrame.setStatus('mandatory')
locIfInOverrun = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 14), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfInOverrun.setStatus('mandatory')
locIfInIgnored = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 15), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfInIgnored.setStatus('mandatory')
locIfInAbort = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 16), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfInAbort.setStatus('mandatory')
locIfResets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 17), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfResets.setStatus('mandatory')
locIfRestarts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 18), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfRestarts.setStatus('mandatory')
locIfKeep = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 19), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfKeep.setStatus('mandatory')
locIfReason = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 20), DisplayString()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfReason.setStatus('mandatory')
locIfCarTrans = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 21), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfCarTrans.setStatus('mandatory')
locIfReliab = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 22), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfReliab.setStatus('mandatory')
locIfDelay = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 23), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfDelay.setStatus('mandatory')
locIfLoad = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 24), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfLoad.setStatus('mandatory')
locIfCollisions = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 25), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfCollisions.setStatus('mandatory')
locIfInputQueueDrops = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 26), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfInputQueueDrops.setStatus('mandatory')
locIfOutputQueueDrops = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 27), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfOutputQueueDrops.setStatus('mandatory')
locIfDescr = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 28), DisplayString()).setMaxAccess("readwrite")
if mibBuilder.loadTexts: locIfDescr.setStatus('mandatory')
locIfSlowInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 30), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfSlowInPkts.setStatus('mandatory')
locIfSlowOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 31), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfSlowOutPkts.setStatus('mandatory')
locIfSlowInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 32), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfSlowInOctets.setStatus('mandatory')
locIfSlowOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 33), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfSlowOutOctets.setStatus('mandatory')
locIfFastInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 34), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFastInPkts.setStatus('mandatory')
locIfFastOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 35), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFastOutPkts.setStatus('mandatory')
locIfFastInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 36), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFastInOctets.setStatus('mandatory')
locIfFastOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 37), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFastOutOctets.setStatus('mandatory')
locIfotherInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 38), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfotherInPkts.setStatus('mandatory')
locIfotherOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 39), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfotherOutPkts.setStatus('mandatory')
locIfotherInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 40), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfotherInOctets.setStatus('mandatory')
locIfotherOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 41), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfotherOutOctets.setStatus('mandatory')
locIfipInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 42), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfipInPkts.setStatus('mandatory')
locIfipOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 43), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfipOutPkts.setStatus('mandatory')
locIfipInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 44), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfipInOctets.setStatus('mandatory')
locIfipOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 45), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfipOutOctets.setStatus('mandatory')
locIfdecnetInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 46), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfdecnetInPkts.setStatus('mandatory')
locIfdecnetOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 47), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfdecnetOutPkts.setStatus('mandatory')
locIfdecnetInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 48), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfdecnetInOctets.setStatus('mandatory')
locIfdecnetOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 49), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfdecnetOutOctets.setStatus('mandatory')
locIfxnsInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 50), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfxnsInPkts.setStatus('mandatory')
locIfxnsOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 51), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfxnsOutPkts.setStatus('mandatory')
locIfxnsInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 52), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfxnsInOctets.setStatus('mandatory')
locIfxnsOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 53), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfxnsOutOctets.setStatus('mandatory')
locIfclnsInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 54), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfclnsInPkts.setStatus('mandatory')
locIfclnsOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 55), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfclnsOutPkts.setStatus('mandatory')
locIfclnsInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 56), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfclnsInOctets.setStatus('mandatory')
locIfclnsOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 57), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfclnsOutOctets.setStatus('mandatory')
locIfappletalkInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 58), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfappletalkInPkts.setStatus('mandatory')
locIfappletalkOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 59), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfappletalkOutPkts.setStatus('mandatory')
locIfappletalkInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 60), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfappletalkInOctets.setStatus('mandatory')
locIfappletalkOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 61), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfappletalkOutOctets.setStatus('mandatory')
locIfnovellInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 62), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfnovellInPkts.setStatus('mandatory')
locIfnovellOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 63), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfnovellOutPkts.setStatus('mandatory')
locIfnovellInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 64), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfnovellInOctets.setStatus('mandatory')
locIfnovellOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 65), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfnovellOutOctets.setStatus('mandatory')
locIfapolloInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 66), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfapolloInPkts.setStatus('mandatory')
locIfapolloOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 67), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfapolloOutPkts.setStatus('mandatory')
locIfapolloInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 68), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfapolloInOctets.setStatus('mandatory')
locIfapolloOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 69), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfapolloOutOctets.setStatus('mandatory')
locIfvinesInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 70), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfvinesInPkts.setStatus('mandatory')
locIfvinesOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 71), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfvinesOutPkts.setStatus('mandatory')
locIfvinesInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 72), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfvinesInOctets.setStatus('mandatory')
locIfvinesOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 73), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfvinesOutOctets.setStatus('mandatory')
locIfbridgedInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 74), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfbridgedInPkts.setStatus('mandatory')
locIfbridgedOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 75), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfbridgedOutPkts.setStatus('mandatory')
locIfbridgedInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 76), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfbridgedInOctets.setStatus('mandatory')
locIfbridgedOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 77), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfbridgedOutOctets.setStatus('mandatory')
locIfsrbInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 78), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfsrbInPkts.setStatus('mandatory')
locIfsrbOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 79), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfsrbOutPkts.setStatus('mandatory')
locIfsrbInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 80), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfsrbInOctets.setStatus('mandatory')
locIfsrbOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 81), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfsrbOutOctets.setStatus('mandatory')
locIfchaosInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 82), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfchaosInPkts.setStatus('mandatory')
locIfchaosOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 83), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfchaosOutPkts.setStatus('mandatory')
locIfchaosInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 84), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfchaosInOctets.setStatus('mandatory')
locIfchaosOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 85), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfchaosOutOctets.setStatus('mandatory')
locIfpupInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 86), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfpupInPkts.setStatus('mandatory')
locIfpupOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 87), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfpupOutPkts.setStatus('mandatory')
locIfpupInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 88), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfpupInOctets.setStatus('mandatory')
locIfpupOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 89), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfpupOutOctets.setStatus('mandatory')
locIfmopInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 90), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfmopInPkts.setStatus('mandatory')
locIfmopOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 91), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfmopOutPkts.setStatus('mandatory')
locIfmopInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 92), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfmopInOctets.setStatus('mandatory')
locIfmopOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 93), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfmopOutOctets.setStatus('mandatory')
locIflanmanInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 94), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIflanmanInPkts.setStatus('mandatory')
locIflanmanOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 95), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIflanmanOutPkts.setStatus('mandatory')
locIflanmanInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 96), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIflanmanInOctets.setStatus('mandatory')
locIflanmanOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 97), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIflanmanOutOctets.setStatus('mandatory')
locIfstunInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 98), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfstunInPkts.setStatus('mandatory')
locIfstunOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 99), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfstunOutPkts.setStatus('mandatory')
locIfstunInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 100), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfstunInOctets.setStatus('mandatory')
locIfstunOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 101), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfstunOutOctets.setStatus('mandatory')
locIfspanInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 102), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfspanInPkts.setStatus('mandatory')
locIfspanOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 103), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfspanOutPkts.setStatus('mandatory')
locIfspanInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 104), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfspanInOctets.setStatus('mandatory')
locIfspanOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 105), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfspanOutOctets.setStatus('mandatory')
locIfarpInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 106), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfarpInPkts.setStatus('mandatory')
locIfarpOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 107), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfarpOutPkts.setStatus('mandatory')
locIfarpInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 108), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfarpInOctets.setStatus('mandatory')
locIfarpOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 109), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfarpOutOctets.setStatus('mandatory')
locIfprobeInPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 110), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfprobeInPkts.setStatus('mandatory')
locIfprobeOutPkts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 111), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfprobeOutPkts.setStatus('mandatory')
locIfprobeInOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 112), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfprobeInOctets.setStatus('mandatory')
locIfprobeOutOctets = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 113), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfprobeOutOctets.setStatus('mandatory')
locIfDribbleInputs = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 1, 1, 114), Counter32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfDribbleInputs.setStatus('mandatory')
lFSIPTable = MibTable((1, 3, 6, 1, 4, 1, 9, 2, 2, 2), )
if mibBuilder.loadTexts: lFSIPTable.setStatus('mandatory')
lFSIPEntry = MibTableRow((1, 3, 6, 1, 4, 1, 9, 2, 2, 2, 1), ).setIndexNames((0, "OLD-CISCO-INTERFACES-MIB", "locIfFSIPIndex"))
if mibBuilder.loadTexts: lFSIPEntry.setStatus('mandatory')
locIfFSIPIndex = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 2, 1, 1), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFSIPIndex.setStatus('mandatory')
locIfFSIPtype = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 2, 1, 2), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3))).clone(namedValues=NamedValues(("notAvailable", 1), ("dte", 2), ("dce", 3)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFSIPtype.setStatus('mandatory')
locIfFSIPrts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 2, 1, 3), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3))).clone(namedValues=NamedValues(("notAvailable", 1), ("up", 2), ("down", 3)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFSIPrts.setStatus('mandatory')
locIfFSIPcts = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 2, 1, 4), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3))).clone(namedValues=NamedValues(("notAvailable", 1), ("up", 2), ("down", 3)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFSIPcts.setStatus('mandatory')
locIfFSIPdtr = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 2, 1, 5), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3))).clone(namedValues=NamedValues(("notAvailable", 1), ("up", 2), ("down", 3)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFSIPdtr.setStatus('mandatory')
locIfFSIPdcd = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 2, 1, 6), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3))).clone(namedValues=NamedValues(("notAvailable", 1), ("up", 2), ("down", 3)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFSIPdcd.setStatus('mandatory')
locIfFSIPdsr = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 2, 2, 1, 7), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3))).clone(namedValues=NamedValues(("notAvailable", 1), ("up", 2), ("down", 3)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: locIfFSIPdsr.setStatus('mandatory')
mibBuilder.exportSymbols("OLD-CISCO-INTERFACES-MIB", locIfLastOutHang=locIfLastOutHang, locIfbridgedOutOctets=locIfbridgedOutOctets, locIfDribbleInputs=locIfDribbleInputs, locIfFSIPrts=locIfFSIPrts, locIfpupOutPkts=locIfpupOutPkts, locIfCarTrans=locIfCarTrans, locIfnovellInOctets=locIfnovellInOctets, locIfpupInOctets=locIfpupInOctets, locIfbridgedInOctets=locIfbridgedInOctets, locIfnovellOutPkts=locIfnovellOutPkts, locIfbridgedInPkts=locIfbridgedInPkts, locIfchaosOutOctets=locIfchaosOutOctets, locIfInputQueueDrops=locIfInputQueueDrops, locIfInBitsSec=locIfInBitsSec, locIfapolloOutPkts=locIfapolloOutPkts, lifEntry=lifEntry, locIfHardType=locIfHardType, locIfvinesOutPkts=locIfvinesOutPkts, locIfclnsOutOctets=locIfclnsOutOctets, locIfappletalkOutPkts=locIfappletalkOutPkts, locIflanmanOutPkts=locIflanmanOutPkts, locIfspanOutPkts=locIfspanOutPkts, lifTable=lifTable, locIfLineProt=locIfLineProt, locIfarpInOctets=locIfarpInOctets, locIflanmanInPkts=locIflanmanInPkts, locIfarpOutPkts=locIfarpOutPkts, locIfappletalkInOctets=locIfappletalkInOctets, locIfRestarts=locIfRestarts, locIfResets=locIfResets, locIfclnsInPkts=locIfclnsInPkts, locIfipInPkts=locIfipInPkts, lFSIPEntry=lFSIPEntry, locIfotherOutPkts=locIfotherOutPkts, locIfSlowOutOctets=locIfSlowOutOctets, locIfdecnetInOctets=locIfdecnetInOctets, locIfipOutPkts=locIfipOutPkts, locIfsrbInPkts=locIfsrbInPkts, locIfsrbInOctets=locIfsrbInOctets, locIfpupOutOctets=locIfpupOutOctets, locIfFSIPcts=locIfFSIPcts, locIfInIgnored=locIfInIgnored, locIfotherInOctets=locIfotherInOctets, locIfFSIPdcd=locIfFSIPdcd, locIfxnsInPkts=locIfxnsInPkts, locIfLastIn=locIfLastIn, locIflanmanOutOctets=locIflanmanOutOctets, locIfdecnetOutPkts=locIfdecnetOutPkts, lFSIPTable=lFSIPTable, locIfchaosInOctets=locIfchaosInOctets, locIfOutBitsSec=locIfOutBitsSec, locIfFastInPkts=locIfFastInPkts, locIfstunOutOctets=locIfstunOutOctets, locIfFastInOctets=locIfFastInOctets, locIfstunInPkts=locIfstunInPkts, locIfchaosOutPkts=locIfchaosOutPkts, locIflanmanInOctets=locIflanmanInOctets, locIfnovellInPkts=locIfnovellInPkts, locIfInCRC=locIfInCRC, locIfFSIPtype=locIfFSIPtype, locIfprobeOutOctets=locIfprobeOutOctets, locIfprobeOutPkts=locIfprobeOutPkts, locIfvinesOutOctets=locIfvinesOutOctets, locIfpupInPkts=locIfpupInPkts, locIfclnsOutPkts=locIfclnsOutPkts, locIfmopOutOctets=locIfmopOutOctets, locIfInGiants=locIfInGiants, locIfprobeInOctets=locIfprobeInOctets, locIfstunOutPkts=locIfstunOutPkts, locIfclnsInOctets=locIfclnsInOctets, locIfvinesInOctets=locIfvinesInOctets, locIfspanInPkts=locIfspanInPkts, locIfxnsOutOctets=locIfxnsOutOctets, locIfapolloInOctets=locIfapolloInOctets, locIfspanInOctets=locIfspanInOctets, locIfCollisions=locIfCollisions, locIfInRunts=locIfInRunts, locIfnovellOutOctets=locIfnovellOutOctets, locIfmopInPkts=locIfmopInPkts, locIfFastOutOctets=locIfFastOutOctets, locIfInAbort=locIfInAbort, locIfappletalkInPkts=locIfappletalkInPkts, locIfFSIPdtr=locIfFSIPdtr, locIfInPktsSec=locIfInPktsSec, locIfLastOut=locIfLastOut, locIfarpInPkts=locIfarpInPkts, locIfappletalkOutOctets=locIfappletalkOutOctets, locIfInOverrun=locIfInOverrun, locIfotherInPkts=locIfotherInPkts, locIfReason=locIfReason, locIfchaosInPkts=locIfchaosInPkts, locIfInFrame=locIfInFrame, locIfxnsOutPkts=locIfxnsOutPkts, locIfReliab=locIfReliab, locIfapolloInPkts=locIfapolloInPkts, locIfstunInOctets=locIfstunInOctets, locIfspanOutOctets=locIfspanOutOctets, locIfdecnetInPkts=locIfdecnetInPkts, locIfOutputQueueDrops=locIfOutputQueueDrops, locIfFastOutPkts=locIfFastOutPkts, locIfmopInOctets=locIfmopInOctets, locIfapolloOutOctets=locIfapolloOutOctets, locIfOutPktsSec=locIfOutPktsSec, linterfaces=linterfaces, locIfbridgedOutPkts=locIfbridgedOutPkts, locIfDescr=locIfDescr, locIfFSIPIndex=locIfFSIPIndex, locIfSlowInPkts=locIfSlowInPkts, locIfFSIPdsr=locIfFSIPdsr, locIfipOutOctets=locIfipOutOctets, locIfarpOutOctets=locIfarpOutOctets, locIfSlowInOctets=locIfSlowInOctets, locIfKeep=locIfKeep, locIfsrbOutPkts=locIfsrbOutPkts, locIfxnsInOctets=locIfxnsInOctets, locIfLoad=locIfLoad, locIfmopOutPkts=locIfmopOutPkts, locIfDelay=locIfDelay, locIfsrbOutOctets=locIfsrbOutOctets, locIfdecnetOutOctets=locIfdecnetOutOctets, locIfvinesInPkts=locIfvinesInPkts, locIfprobeInPkts=locIfprobeInPkts, locIfipInOctets=locIfipInOctets, locIfotherOutOctets=locIfotherOutOctets, locIfSlowOutPkts=locIfSlowOutPkts)
