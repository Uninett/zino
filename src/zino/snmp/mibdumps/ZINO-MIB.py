# SNMP MIB module (ZINO-MIB) expressed in pysnmp data model.
#
# This Python module is designed to be imported and executed by the
# pysnmp library.
#
# See https://www.pysnmp.com/pysnmp for further information.
#
# Notes
# -----
# ASN.1 source file://./ZINO-MIB.my
# Produced by pysmi-1.6.2 at Thu Oct  2 13:15:57 2025
# On host agrajag platform Linux version 6.12.49 by user mvold
# Using Python version 3.12.7 (main, Oct 16 2024, 04:37:19) [Clang 18.1.8 ]

if 'mibBuilder' not in globals():
    import sys

    sys.stderr.write(__doc__)
    sys.exit(1)

# Import base ASN.1 objects even if this MIB does not use it

(Integer,
 OctetString,
 ObjectIdentifier) = mibBuilder.importSymbols(
    "ASN1",
    "Integer",
    "OctetString",
    "ObjectIdentifier")

(NamedValues,) = mibBuilder.importSymbols(
    "ASN1-ENUMERATION",
    "NamedValues")
(ConstraintsIntersection,
 ConstraintsUnion,
 SingleValueConstraint,
 ValueRangeConstraint,
 ValueSizeConstraint) = mibBuilder.importSymbols(
    "ASN1-REFINEMENT",
    "ConstraintsIntersection",
    "ConstraintsUnion",
    "SingleValueConstraint",
    "ValueRangeConstraint",
    "ValueSizeConstraint")

# Import SMI symbols from the MIBs this MIB depends on

(ModuleCompliance,
 NotificationGroup) = mibBuilder.importSymbols(
    "SNMPv2-CONF",
    "ModuleCompliance",
    "NotificationGroup")

(Bits,
 Counter32,
 Counter64,
 Gauge32,
 Integer32,
 IpAddress,
 ModuleIdentity,
 MibIdentifier,
 NotificationType,
 ObjectIdentity,
 MibScalar,
 MibTable,
 MibTableRow,
 MibTableColumn,
 TimeTicks,
 Unsigned32,
 iso) = mibBuilder.importSymbols(
    "SNMPv2-SMI",
    "Bits",
    "Counter32",
    "Counter64",
    "Gauge32",
    "Integer32",
    "IpAddress",
    "ModuleIdentity",
    "MibIdentifier",
    "NotificationType",
    "ObjectIdentity",
    "MibScalar",
    "MibTable",
    "MibTableRow",
    "MibTableColumn",
    "TimeTicks",
    "Unsigned32",
    "iso")

(DateAndTime,
 DisplayString,
 PhysAddress,
 TextualConvention,
 TimeInterval,
 TimeStamp) = mibBuilder.importSymbols(
    "SNMPv2-TC",
    "DateAndTime",
    "DisplayString",
    "PhysAddress",
    "TextualConvention",
    "TimeInterval",
    "TimeStamp")

(uninettMibs,
 zinoMIB) = mibBuilder.importSymbols(
    "UNINETT-SMI",
    "uninettMibs",
    "zinoMIB")


# MODULE-IDENTITY

zinoMIB = ModuleIdentity(
    (1, 3, 6, 1, 4, 1, 2428, 130, 1)
)
if mibBuilder.loadTexts:
    zinoMIB.setLastUpdated("201201190000Z")
if mibBuilder.loadTexts:
    zinoMIB.setOrganization("UNINETT AS")
if mibBuilder.loadTexts:
    zinoMIB.setContactInfo(" UNINETT AS NO-7465 Trondheim Norway E-mail: drift@uninett.no")
if mibBuilder.loadTexts:
    zinoMIB.setDescription("The MIB for zino keepalive / polling.")


# Types definitions


# TEXTUAL-CONVENTIONS



# MIB Managed Objects in the order of their OIDs

_ZinoMIBObjects_ObjectIdentity = ObjectIdentity
zinoMIBObjects = _ZinoMIBObjects_ObjectIdentity(
    (1, 3, 6, 1, 4, 1, 2428, 130, 1, 1)
)
_ZinoUpTime_Type = Counter32
_ZinoUpTime_Object = MibScalar
zinoUpTime = _ZinoUpTime_Object(
    (1, 3, 6, 1, 4, 1, 2428, 130, 1, 1, 1),
    _ZinoUpTime_Type()
)
zinoUpTime.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    zinoUpTime.setStatus("mandatory")
if mibBuilder.loadTexts:
    zinoUpTime.setDescription("The time (in seconds) since this zino server instance was re-initialized.")

# Managed Objects groups


# Notification objects


# Notifications groups


# Agent capabilities


# Module compliance


# Export all MIB objects to the MIB builder

mibBuilder.exportSymbols(
    "ZINO-MIB",
    **{"zinoMIB": zinoMIB,
       "zinoMIBObjects": zinoMIBObjects,
       "zinoUpTime": zinoUpTime}
)
