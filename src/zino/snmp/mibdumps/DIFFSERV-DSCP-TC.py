#
# PySNMP MIB module DIFFSERV-DSCP-TC (http://snmplabs.com/pysmi)
# ASN.1 source file:///usr/share/snmp/mibs/ietf/DIFFSERV-DSCP-TC
# Produced by pysmi-1.1.10 at Mon Oct  9 12:14:08 2023
# On host simtve-ThinkPad-X1-Carbon-Gen-9 platform Linux version 5.15.0-84-generic by user simon
# Using Python version 3.9.18 (main, Aug 25 2023, 13:20:04) 
#
Integer, ObjectIdentifier, OctetString = mibBuilder.importSymbols("ASN1", "Integer", "ObjectIdentifier", "OctetString")
NamedValues, = mibBuilder.importSymbols("ASN1-ENUMERATION", "NamedValues")
ConstraintsUnion, ValueRangeConstraint, ValueSizeConstraint, ConstraintsIntersection, SingleValueConstraint = mibBuilder.importSymbols("ASN1-REFINEMENT", "ConstraintsUnion", "ValueRangeConstraint", "ValueSizeConstraint", "ConstraintsIntersection", "SingleValueConstraint")
NotificationGroup, ModuleCompliance = mibBuilder.importSymbols("SNMPv2-CONF", "NotificationGroup", "ModuleCompliance")
IpAddress, ModuleIdentity, Bits, MibIdentifier, Counter64, Integer32, iso, TimeTicks, NotificationType, Unsigned32, mib_2, MibScalar, MibTable, MibTableRow, MibTableColumn, ObjectIdentity, Gauge32, Counter32 = mibBuilder.importSymbols("SNMPv2-SMI", "IpAddress", "ModuleIdentity", "Bits", "MibIdentifier", "Counter64", "Integer32", "iso", "TimeTicks", "NotificationType", "Unsigned32", "mib-2", "MibScalar", "MibTable", "MibTableRow", "MibTableColumn", "ObjectIdentity", "Gauge32", "Counter32")
DisplayString, TextualConvention = mibBuilder.importSymbols("SNMPv2-TC", "DisplayString", "TextualConvention")
diffServDSCPTC = ModuleIdentity((1, 3, 6, 1, 2, 1, 96))
diffServDSCPTC.setRevisions(('2002-05-09 00:00',))

if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    if mibBuilder.loadTexts: diffServDSCPTC.setRevisionsDescriptions(('Initial version, published as RFC 3289.',))
if mibBuilder.loadTexts: diffServDSCPTC.setLastUpdated('200205090000Z')
if mibBuilder.loadTexts: diffServDSCPTC.setOrganization('IETF Differentiated Services WG')
if mibBuilder.loadTexts: diffServDSCPTC.setContactInfo(' Fred Baker Cisco Systems 1121 Via Del Rey Santa Barbara, CA 93117, USA E-mail: fred@cisco.com Kwok Ho Chan Nortel Networks 600 Technology Park Drive Billerica, MA 01821, USA E-mail: khchan@nortelnetworks.com Andrew Smith Harbour Networks Jiuling Building 21 North Xisanhuan Ave. Beijing, 100089, PRC E-mail: ah_smith@acm.org Differentiated Services Working Group: diffserv@ietf.org')
if mibBuilder.loadTexts: diffServDSCPTC.setDescription('The Textual Conventions defined in this module should be used whenever a Differentiated Services Code Point is used in a MIB.')
class Dscp(TextualConvention, Integer32):
    reference = 'RFC 2474, RFC 2780'
    description = 'A Differentiated Services Code-Point that may be used for marking a traffic stream.'
    status = 'current'
    displayHint = 'd'
    subtypeSpec = Integer32.subtypeSpec + ValueRangeConstraint(0, 63)

class DscpOrAny(TextualConvention, Integer32):
    reference = 'RFC 2474, RFC 2780'
    description = 'The IP header Differentiated Services Code-Point that may be used for discriminating among traffic streams. The value -1 is used to indicate a wild card i.e. any value.'
    status = 'current'
    displayHint = 'd'
    subtypeSpec = Integer32.subtypeSpec + ConstraintsUnion(ValueRangeConstraint(-1, -1), ValueRangeConstraint(0, 63), )
mibBuilder.exportSymbols("DIFFSERV-DSCP-TC", DscpOrAny=DscpOrAny, Dscp=Dscp, PYSNMP_MODULE_ID=diffServDSCPTC, diffServDSCPTC=diffServDSCPTC)
