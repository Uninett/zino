#
# PySNMP MIB module OLD-CISCO-TS-MIB (http://snmplabs.com/pysmi)
# ASN.1 source file:///home/mvold/mibs/cisco/OLD-CISCO-TS-MIB.my
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
lts = MibIdentifier((1, 3, 6, 1, 4, 1, 9, 2, 9))
tsLines = MibScalar((1, 3, 6, 1, 4, 1, 9, 2, 9, 1), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLines.setStatus('mandatory')
ltsLineTable = MibTable((1, 3, 6, 1, 4, 1, 9, 2, 9, 2), )
if mibBuilder.loadTexts: ltsLineTable.setStatus('mandatory')
ltsLineEntry = MibTableRow((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1), ).setIndexNames((0, "OLD-CISCO-TS-MIB", "tsLineNumber"))
if mibBuilder.loadTexts: ltsLineEntry.setStatus('mandatory')
tsLineActive = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 1), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineActive.setStatus('mandatory')
tsLineType = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 2), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3, 4, 5, 6))).clone(namedValues=NamedValues(("unknown", 1), ("console", 2), ("terminal", 3), ("line-printer", 4), ("virtual-terminal", 5), ("auxiliary", 6)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineType.setStatus('mandatory')
tsLineAutobaud = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 3), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineAutobaud.setStatus('mandatory')
tsLineSpeedin = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 4), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineSpeedin.setStatus('mandatory')
tsLineSpeedout = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 5), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineSpeedout.setStatus('mandatory')
tsLineFlow = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 6), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3, 4, 5, 6, 7, 8))).clone(namedValues=NamedValues(("unknown", 1), ("none", 2), ("software-input", 3), ("software-output", 4), ("software-both", 5), ("hardware-input", 6), ("hardware-output", 7), ("hardware-both", 8)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineFlow.setStatus('mandatory')
tsLineModem = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 7), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3, 4, 5, 6, 7))).clone(namedValues=NamedValues(("unknown", 1), ("none", 2), ("call-in", 3), ("call-out", 4), ("cts-required", 5), ("ri-is-cd", 6), ("inout", 7)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineModem.setStatus('mandatory')
tsLineLoc = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 8), DisplayString()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineLoc.setStatus('mandatory')
tsLineTerm = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 9), DisplayString()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineTerm.setStatus('mandatory')
tsLineScrlen = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 10), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineScrlen.setStatus('mandatory')
tsLineScrwid = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 11), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineScrwid.setStatus('mandatory')
tsLineEsc = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 12), DisplayString()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineEsc.setStatus('mandatory')
tsLineTmo = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 13), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineTmo.setStatus('mandatory')
tsLineSestmo = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 14), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineSestmo.setStatus('mandatory')
tsLineRotary = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 15), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineRotary.setStatus('mandatory')
tsLineUses = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 16), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineUses.setStatus('mandatory')
tsLineNses = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 17), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineNses.setStatus('mandatory')
tsLineUser = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 18), DisplayString()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineUser.setStatus('mandatory')
tsLineNoise = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 19), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineNoise.setStatus('mandatory')
tsLineNumber = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 20), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineNumber.setStatus('mandatory')
tsLineTimeActive = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 2, 1, 21), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tsLineTimeActive.setStatus('mandatory')
ltsLineSessionTable = MibTable((1, 3, 6, 1, 4, 1, 9, 2, 9, 3), )
if mibBuilder.loadTexts: ltsLineSessionTable.setStatus('mandatory')
ltsLineSessionEntry = MibTableRow((1, 3, 6, 1, 4, 1, 9, 2, 9, 3, 1), ).setIndexNames((0, "OLD-CISCO-TS-MIB", "tslineSesLine"), (0, "OLD-CISCO-TS-MIB", "tslineSesSession"))
if mibBuilder.loadTexts: ltsLineSessionEntry.setStatus('mandatory')
tslineSesType = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 3, 1, 1), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11))).clone(namedValues=NamedValues(("unknown", 1), ("pad", 2), ("stream", 3), ("rlogin", 4), ("telnet", 5), ("tcp", 6), ("lat", 7), ("mop", 8), ("slip", 9), ("xremote", 10), ("rshell", 11)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: tslineSesType.setStatus('mandatory')
tslineSesDir = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 3, 1, 2), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3))).clone(namedValues=NamedValues(("unknown", 1), ("incoming", 2), ("outgoing", 3)))).setMaxAccess("readonly")
if mibBuilder.loadTexts: tslineSesDir.setStatus('mandatory')
tslineSesAddr = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 3, 1, 3), IpAddress()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tslineSesAddr.setStatus('mandatory')
tslineSesName = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 3, 1, 4), DisplayString()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tslineSesName.setStatus('mandatory')
tslineSesCur = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 3, 1, 5), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tslineSesCur.setStatus('mandatory')
tslineSesIdle = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 3, 1, 6), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tslineSesIdle.setStatus('mandatory')
tslineSesLine = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 3, 1, 7), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tslineSesLine.setStatus('mandatory')
tslineSesSession = MibTableColumn((1, 3, 6, 1, 4, 1, 9, 2, 9, 3, 1, 8), Integer32()).setMaxAccess("readonly")
if mibBuilder.loadTexts: tslineSesSession.setStatus('mandatory')
tsMsgTtyLine = MibScalar((1, 3, 6, 1, 4, 1, 9, 2, 9, 4), Integer32()).setMaxAccess("readwrite")
if mibBuilder.loadTexts: tsMsgTtyLine.setStatus('mandatory')
tsMsgIntervaltim = MibScalar((1, 3, 6, 1, 4, 1, 9, 2, 9, 5), Integer32()).setMaxAccess("readwrite")
if mibBuilder.loadTexts: tsMsgIntervaltim.setStatus('mandatory')
tsMsgDuration = MibScalar((1, 3, 6, 1, 4, 1, 9, 2, 9, 6), Integer32()).setMaxAccess("readwrite")
if mibBuilder.loadTexts: tsMsgDuration.setStatus('mandatory')
tsMsgText = MibScalar((1, 3, 6, 1, 4, 1, 9, 2, 9, 7), DisplayString()).setMaxAccess("readwrite")
if mibBuilder.loadTexts: tsMsgText.setStatus('mandatory')
tsMsgTmpBanner = MibScalar((1, 3, 6, 1, 4, 1, 9, 2, 9, 8), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2))).clone(namedValues=NamedValues(("no", 1), ("additive", 2)))).setMaxAccess("readwrite")
if mibBuilder.loadTexts: tsMsgTmpBanner.setStatus('mandatory')
tsMsgSend = MibScalar((1, 3, 6, 1, 4, 1, 9, 2, 9, 9), Integer32().subtype(subtypeSpec=ConstraintsUnion(SingleValueConstraint(1, 2, 3, 4))).clone(namedValues=NamedValues(("nothing", 1), ("reload", 2), ("messagedone", 3), ("abort", 4)))).setMaxAccess("readwrite")
if mibBuilder.loadTexts: tsMsgSend.setStatus('mandatory')
tsClrTtyLine = MibScalar((1, 3, 6, 1, 4, 1, 9, 2, 9, 10), Integer32()).setMaxAccess("readwrite")
if mibBuilder.loadTexts: tsClrTtyLine.setStatus('mandatory')
mibBuilder.exportSymbols("OLD-CISCO-TS-MIB", tsLines=tsLines, ltsLineSessionEntry=ltsLineSessionEntry, tsLineNumber=tsLineNumber, tsLineFlow=tsLineFlow, tsLineNoise=tsLineNoise, tsClrTtyLine=tsClrTtyLine, tsLineTimeActive=tsLineTimeActive, tslineSesType=tslineSesType, tsLineLoc=tsLineLoc, ltsLineEntry=ltsLineEntry, tsLineActive=tsLineActive, tsLineNses=tsLineNses, tslineSesSession=tslineSesSession, ltsLineTable=ltsLineTable, tsLineRotary=tsLineRotary, tsLineScrwid=tsLineScrwid, tsLineTerm=tsLineTerm, tsLineUses=tsLineUses, tsLineAutobaud=tsLineAutobaud, tsLineEsc=tsLineEsc, tsLineModem=tsLineModem, ltsLineSessionTable=ltsLineSessionTable, tsLineTmo=tsLineTmo, tslineSesName=tslineSesName, tsMsgTtyLine=tsMsgTtyLine, tslineSesDir=tslineSesDir, tsLineType=tsLineType, tslineSesIdle=tslineSesIdle, tslineSesLine=tslineSesLine, tsMsgSend=tsMsgSend, tsMsgTmpBanner=tsMsgTmpBanner, tsLineScrlen=tsLineScrlen, tsLineSpeedout=tsLineSpeedout, tsMsgText=tsMsgText, lts=lts, tsLineSpeedin=tsLineSpeedin, tsLineSestmo=tsLineSestmo, tslineSesCur=tslineSesCur, tsMsgDuration=tsMsgDuration, tsLineUser=tsLineUser, tsMsgIntervaltim=tsMsgIntervaltim, tslineSesAddr=tslineSesAddr)
