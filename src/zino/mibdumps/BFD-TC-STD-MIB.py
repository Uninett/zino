#
# PySNMP MIB module BFD-TC-STD-MIB (http://snmplabs.com/pysmi)
# ASN.1 source file://./BFD-TC-STD-MIB.mib
# Produced by pysmi-1.1.10 at Mon Oct  9 12:14:08 2023
# On host simtve-ThinkPad-X1-Carbon-Gen-9 platform Linux version 5.15.0-84-generic by user simon
# Using Python version 3.9.18 (main, Aug 25 2023, 13:20:04) 
#
Integer, ObjectIdentifier, OctetString = mibBuilder.importSymbols("ASN1", "Integer", "ObjectIdentifier", "OctetString")
NamedValues, = mibBuilder.importSymbols("ASN1-ENUMERATION", "NamedValues")
ConstraintsUnion, ValueRangeConstraint, ValueSizeConstraint, ConstraintsIntersection, SingleValueConstraint = mibBuilder.importSymbols("ASN1-REFINEMENT", "ConstraintsUnion", "ValueRangeConstraint", "ValueSizeConstraint", "ConstraintsIntersection", "SingleValueConstraint")
NotificationGroup, ModuleCompliance = mibBuilder.importSymbols("SNMPv2-CONF", "NotificationGroup", "ModuleCompliance")
IpAddress, ModuleIdentity, Bits, MibIdentifier, Counter64, iso, Integer32, TimeTicks, NotificationType, Unsigned32, mib_2, MibScalar, MibTable, MibTableRow, MibTableColumn, ObjectIdentity, Gauge32, Counter32 = mibBuilder.importSymbols("SNMPv2-SMI", "IpAddress", "ModuleIdentity", "Bits", "MibIdentifier", "Counter64", "iso", "Integer32", "TimeTicks", "NotificationType", "Unsigned32", "mib-2", "MibScalar", "MibTable", "MibTableRow", "MibTableColumn", "ObjectIdentity", "Gauge32", "Counter32")
DisplayString, TextualConvention = mibBuilder.importSymbols("SNMPv2-TC", "DisplayString", "TextualConvention")
bfdTCStdMib = ModuleIdentity((1, 3, 6, 1, 2, 1, 223))
bfdTCStdMib.setRevisions(('2014-08-12 00:00',))

if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    if mibBuilder.loadTexts: bfdTCStdMib.setRevisionsDescriptions(('Initial version. Published as RFC 7330.',))
if mibBuilder.loadTexts: bfdTCStdMib.setLastUpdated('201408120000Z')
if mibBuilder.loadTexts: bfdTCStdMib.setOrganization('IETF Bidirectional Forwarding Detection Working Group')
if mibBuilder.loadTexts: bfdTCStdMib.setContactInfo('Thomas D. Nadeau Brocade Email: tnadeau@lucidvision.com Zafar Ali Cisco Systems, Inc. Email: zali@cisco.com Nobo Akiya Cisco Systems, Inc. Email: nobo@cisco.com Comments about this document should be emailed directly to the BFD working group mailing list at rtg-bfd@ietf.org')
if mibBuilder.loadTexts: bfdTCStdMib.setDescription("Copyright (c) 2014 IETF Trust and the persons identified as authors of the code. All rights reserved. Redistribution and use in source and binary forms, with or without modification, is permitted pursuant to, and subject to the license terms contained in, the Simplified BSD License set forth in Section 4.c of the IETF Trust's Legal Provisions Relating to IETF Documents (http://trustee.ietf.org/license-info).")
class BfdSessIndexTC(TextualConvention, Unsigned32):
    description = 'An index used to uniquely identify BFD sessions.'
    status = 'current'
    displayHint = 'd'
    subtypeSpec = Unsigned32.subtypeSpec + ValueRangeConstraint(1, 4294967295)

class BfdIntervalTC(TextualConvention, Unsigned32):
    description = 'The BFD interval in microseconds.'
    status = 'current'
    displayHint = 'd'
    subtypeSpec = Unsigned32.subtypeSpec + ValueRangeConstraint(0, 4294967295)

class BfdMultiplierTC(TextualConvention, Unsigned32):
    description = 'The BFD failure detection multiplier.'
    status = 'current'
    displayHint = 'd'
    subtypeSpec = Unsigned32.subtypeSpec + ValueRangeConstraint(1, 255)

class BfdCtrlDestPortNumberTC(TextualConvention, Unsigned32):
    reference = 'Use of port 3784 from Katz, D. and D. Ward, Bidirectional Forwarding Detection (BFD) for IPv4 and IPv6 (Single Hop), RFC 5881, June 2010. Use of port 4784 from Katz, D. and D. Ward, Bidirectional Forwarding Detection (BFD) for Multihop Paths, RFC 5883, June 2010. Use of port 6784 from Bhatia, M., Chen, M., Boutros, S., Binderberger, M., and J. Haas, Bidirectional Forwarding Detection (BFD) on Link Aggregation Group (LAG) Interfaces, RFC 7130, February 2014.'
    description = 'UDP destination port number of BFD control packets. 3784 represents single-hop BFD session. 4784 represents multi-hop BFD session. 6784 represents BFD on Link Aggregation Group (LAG) session. However, syntax is left open to wider range of values purposely for two reasons: 1. Implementation uses non-compliant port number for valid proprietary reason. 2. Potential future extension documents. The value of 0 is a special, reserved value used to indicate special conditions and should not be considered a valid port number.'
    status = 'current'
    displayHint = 'd'
    subtypeSpec = Unsigned32.subtypeSpec + ValueRangeConstraint(0, 65535)

class BfdCtrlSourcePortNumberTC(TextualConvention, Unsigned32):
    reference = 'Port 49152..65535 from RFC5881'
    description = 'UDP source port number of BFD control packets. However, syntax is left open to wider range of values purposely for two reasons: 1. Implementation uses non-compliant port number for valid proprietary reason. 2. Potential future extension documents. The value of 0 is a special, reserved value used to indicate special conditions and should not be considered a valid port number.'
    status = 'current'
    displayHint = 'd'
    subtypeSpec = Unsigned32.subtypeSpec + ValueRangeConstraint(0, 65535)

mibBuilder.exportSymbols("BFD-TC-STD-MIB", BfdCtrlDestPortNumberTC=BfdCtrlDestPortNumberTC, PYSNMP_MODULE_ID=bfdTCStdMib, BfdSessIndexTC=BfdSessIndexTC, BfdMultiplierTC=BfdMultiplierTC, BfdCtrlSourcePortNumberTC=BfdCtrlSourcePortNumberTC, BfdIntervalTC=BfdIntervalTC, bfdTCStdMib=bfdTCStdMib)
