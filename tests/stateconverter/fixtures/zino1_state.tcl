global ::AddrToRouter
set ::AddrToRouter(175.46.88.27) "boot-gw1"
global ::BootTime
set ::BootTime(boot-gw1) "1705257668"
global ::EventAttrs_100
set ::EventAttrs_100(bgpAS) "running"
set ::EventAttrs_100(bgpOS) "down"
set ::EventAttrs_100(history) "{1706257668 state change embryonic -> open (monitor)}"
set ::EventAttrs_100(id) "100"
set ::EventAttrs_100(lastevent) "peer is down"
set ::EventAttrs_100(log) "{1706257668 auroralane-gw1 peer 0515:7cfd:1bcc:279e:f5a4:5528:f4c3:58af AS 100 is down (running)}"
set ::EventAttrs_100(opened) "1706257668"
set ::EventAttrs_100(peer-uptime) "420"
set ::EventAttrs_100(polladdr) "219.188.192.78"
set ::EventAttrs_100(priority) "100"
set ::EventAttrs_100(remote-AS) "100"
set ::EventAttrs_100(remote-addr) "0515:7cfd:1bcc:279e:f5a4:5528:f4c3:58af"
set ::EventAttrs_100(router) "auroralane-gw1"
set ::EventAttrs_100(state) "waiting"
set ::EventAttrs_100(type) "bgp"
set ::EventAttrs_100(updated) "1706257668"
global ::EventAttrs_110
set ::EventAttrs_110(ac-down) "15000000"
set ::EventAttrs_110(descr) "LACP-link, test.no-phy1"
set ::EventAttrs_110(flaps) "10"
set ::EventAttrs_110(flapstate) "stable"
set ::EventAttrs_110(history) "{1686257668 state change embryonic -> open (monitor)}
set ::EventAttrs_110(ifindex) "150"
set ::EventAttrs_110(lasttrans) "1686257668"
set ::EventAttrs_110(log) "{1686257668 arkham-sw1: intf \"ge-1/0/10\" ix 150 linkDown}
set ::EventAttrs_110(opened) "1686257668"
set ::EventAttrs_110(polladdr) "53.44.228.67"
set ::EventAttrs_110(port) "ge-1/0/10"
set ::EventAttrs_110(portstate) "up"
set ::EventAttrs_110(priority) "100"
set ::EventAttrs_110(router) "arkham-sw1"
set ::EventAttrs_110(state) "ignored"
set ::EventAttrs_110(type) "portstate"
set ::EventAttrs_110(updated) "1686257668"
global ::EventAttrs_146
set ::EventAttrs_146(alarm-count) "1"
set ::EventAttrs_146(alarm-type) "yellow"
set ::EventAttrs_146(history) "{1696257668 state change embryonic -> open (monitor)} {1697257668 Ack}"
set ::EventAttrs_146(id) "146"
set ::EventAttrs_146(lastevent) "alarms went from 0 to 1"
set ::EventAttrs_146(log) "{1696257668 whoville-gw1 yellow alarms went from 0 to 1} {1699257668 Random log}"
set ::EventAttrs_146(opened) "1696257668"
set ::EventAttrs_146(polladdr) "176.53.125.80"
set ::EventAttrs_146(priority) "300"
set ::EventAttrs_146(router) "whoville-gw1"
set ::EventAttrs_146(state) "waiting"
set ::EventAttrs_146(type) "alarm"
set ::EventAttrs_146(updated) "1696257668"
global ::EventAttrs_200
set ::EventAttrs_200(Neigh-rDNS) "nissen.nordpolen.no"
set ::EventAttrs_200(bfdAddr) "219.188.192.78"
set ::EventAttrs_200(bfdDiscr) "4500"
set ::EventAttrs_200(bfdIx) "30"
set ::EventAttrs_200(bfdState) "down"
set ::EventAttrs_200(history) "{1700400123 state change embryonic -> open (monitor)}"
set ::EventAttrs_200(id) "200"
set ::EventAttrs_200(lastevent) "changed from up to adminDown (poll)"
set ::EventAttrs_200(log) "{1700400123 blaafjell-gw2 BFD neighbor 219.188.192.78 (nissen.nordpolen.no) changed from up to down (trap) diag neighborSignaledSessionDown}"
set ::EventAttrs_200(opened) "1700400123"
set ::EventAttrs_200(polladdr) "93.150.77.115"
set ::EventAttrs_200(priority) "100"
set ::EventAttrs_200(router) "blaafjell-gw2"
set ::EventAttrs_200(state) "open"
set ::EventAttrs_200(type) "bfd"
set ::EventAttrs_200(updated) "1700400123"
global ::EventCloseTimes
global ::EventId
set ::EventId(auroralane-gw1,30:00:04:AB:05:54:00:01:00:00:00:00:00:00:00:AA,bgp) "100"
set ::EventId(arkham-sw1,150,portstate) "110"
set ::EventId(whoville-gw1,yellow,alarm) "146"
set ::EventId(blaafjell-gw2,30,bfd) "200"
global ::EventIdToIx
set ::EventIdToIx(100) "auroralane-gw1,30:00:04:AB:05:54:00:01:00:00:00:00:00:00:00:AA,bgp"
set ::EventIdToIx(110) "arkham-sw1,150,portstate"
set ::EventIdToIx(146) "whoville-gw1,yellow,alarm"
set ::EventIdToIx(200) "blaafjell-gw2,30,bfd"
set ::JNXalarms(whoville-gw1,red) "0"
set ::JNXalarms(whoville-gw1,yellow) "1"
set ::bfdSessState(blaafjell-gw2,30) "down"
set ::bfdSessAddr(blaafjell-gw2,30) "219.188.192.78"
set ::bfdSessDiscr(blaafjell-gw2,30) "4500"
set ::bfdSessAddrType(blaafjell-gw2,30) "ipv4"
set ::portState(arkham-sw1,150) "up"
set ::portToIfDescr(arkham-sw1,150) "ge-1/0/10"
set ::portToLocIfDescr(arkham-sw1,150) "LACP-link, test.no-phy1"
set ::bgpPeerAdminState(auroralane-gw1,30:00:04:AB:05:54:00:01:00:00:00:00:00:00:00:AA) "running"
set ::bgpPeerOperState(auroralane-gw1,30:00:04:AB:05:54:00:01:00:00:00:00:00:00:00:AA) "active"
set ::bgpPeerUpTime(auroralane-gw1,30:00:04:AB:05:54:00:01:00:00:00:00:00:00:00:AA) "14000000"
set ::bgpPeers(auroralane-gw1) "30:00:04:AB:05:54:00:01:00:00:00:00:00:00:00:AA"
set ::isJuniper(juniper-gw1) "1"
set ::isCisco(juniper-gw1) "0"
set ::isJuniper(cisco-gw1) "0"
set ::isCisco(cisco-gw1) "1"
global ::pm::event_3188
set ::pm::event_3188(endtime) "1720025126"
set ::pm::event_3188(match_dev) "blaafjell-gw2"
set ::pm::event_3188(match_expr) "ge-1/0/10"
set ::pm::event_3188(match_type) "intf-regexp"
set ::pm::event_3188(starttime) "1720021526"
set ::pm::event_3188(type) "portstate"
set ::pm::event_3188(log) "{1720021529 logmessage}"
global ::pm::events
set ::pm::events(3188) "1"
global ::pm::lastid
set ::pm::lastid "3188"
global ::pm::lasttime
set ::pm::lasttime "1720018082"
global ::pm::pm_events
set ::pm::pm_events(3188) "110"
