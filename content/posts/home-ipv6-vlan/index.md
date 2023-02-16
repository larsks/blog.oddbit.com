---
categories: [tech]
title: Setting up an IPv6 VLAN
date: "2022-11-16"
tags:
- networking
- ipv6
- vlan
- edgerouter
- nmcli
- networkmanager
---

My internet service provider ([FIOS][]) doesn't yet (sad face) offer IPv6 capable service, so I've set up an IPv6 tunnel using the [Hurricane Electric][he.net] tunnel broker. I want to provide IPv6 connectivity to multiple systems in my house, but not to **all** systems in my house [^1]. In order to meet those requirements, I'm going to set up the tunnel on the router, and then expose connectivity over an IPv6-only VLAN. In this post, we'll walk through the steps necessary to set that up.

[fios]: https://www.verizon.com/home/fios/
[he.net]: https://www.tunnelbroker.net/

[^1]: Some services (Netflix is a notable example) block access over the IPv6 tunnels because it breaks their geolocation process and prevents them from determining your country of origin. I don't want to break things for other folks in my house just because I want to play with IPv6.

Parts of this post are going to be device specific: for example, I'm using a Ubiquiti [EdgeRouter X][] as my Internet router, so the tunnel setup is going to be specific to that device. The section about setting things up on my Linux desktop will be more generally applicable.

[edgerouter x]: https://store.ui.com/collections/operator-edgemax-routers/products/edgerouter-x

There are three major parts to this post:

- [Configure the EdgeRouter](#configure-the-edgerouter)

  This shows how to set up an IPv6 tunnel and configure an IPv6-only
  VLAN on the EdgeRouter.

- [Configure the switch](#configure-the-switch)

  This is only necessary due to the specifics of the connection between
  my desktop and the router; you can probably skip this.

- [Configure the desktop](#configure-the-desktop)

  This shows how to set up the IPv6 VLAN interface under Linux using `nmcli`.

## What we know

When you set up an IPv6 tunnel with hurricane electric, you receive several bits of information. We care in particular about the following (the IPv6 addresses and client IPv4 addresses here have been munged for privacy reasons):

### IPv6 Tunnel Endpoints

|                     |                          |
|---------------------|--------------------------|
| Server IPv4 Address | 209.51.161.14            |
| Server IPv6 Address | 2001:470:1236:1212::1/64 |
| Client IPv4 Address | 1.2.3.4                  |
| Client IPv6 Address | 2001:470:1236:1212::2/64 |

### Routed IPv6 Prefixes

|            |                         |
|------------|-------------------------|
| Routed /64 | 2001:470:1237:1212::/64 |

We'll refer back to this information as we configured things later on.

## Configure the EdgeRouter

### Create the tunnel interface

The first step in the process is to create a tunnel interface -- that is, an interface that looks like an ordinary network interface, but is in fact encapsulating traffic and sending it to the tunnel broker where it will unpacked and sent on its way.

I'll be creating a [SIT][] tunnel, which is designed to "interconnect isolated IPv6 networks" over an IPv4 connection.

[sit]: https://wiki.linuxfoundation.org/networking/tunneling#sit_tunnels

I start by setting the tunnel encapsulation type and assigning an IPv6 address to the tunnel interface. This is the "Client IPv6 Address" from the earlier table:

```
set interfaces tunnel tun0 encapsulation sit
set interfaces tunnel tun0 address 2001:470:1236:1212::2/64
```

Next I need to define the local and remote IPv4 endpoints of the tunnel. The remote endpoint is the "Server IPv4" address.  The value `0.0.0.0` for the `local-ip` option means "whichever source address is appropriate for connecting to the given remote address":

```
set interfaces tunnel tun0 remote-ip 209.51.161.14
set interfaces tunnel tun0 local-ip 0.0.0.0
```

Finally, I associate some firewall rulesets with the interface. This is import because, unlike IPv4, as you assign IPv6 addresses to internal devices they will be *directly connected to the internet*. With no firewall rules in place you would find yourself inadvertently exposing services that previously were "behind" your home router.

```
set interfaces tunnel tun0 firewall in ipv6-name WANv6_IN
set interfaces tunnel tun0 firewall local ipv6-name WANv6_LOCAL
```

I'm using the existing `WANv6_IN` and `WANv6_LOCAL` rulesets, which by default block all inbound traffic. These correspond to the following `ip6tables` chains:

```
root@ubnt:~# ip6tables -S WANv6_IN
-N WANv6_IN
-A WANv6_IN -m comment --comment WANv6_IN-10 -m state --state RELATED,ESTABLISHED -j RETURN
-A WANv6_IN -m comment --comment WANv6_IN-20 -m state --state INVALID -j DROP
-A WANv6_IN -m comment --comment "WANv6_IN-10000 default-action drop" -j LOG --log-prefix "[WANv6_IN-default-D]"
-A WANv6_IN -m comment --comment "WANv6_IN-10000 default-action drop" -j DROP
root@ubnt:~# ip6tables -S WANv6_LOCAL
-N WANv6_LOCAL
-A WANv6_LOCAL -m comment --comment WANv6_LOCAL-10 -m state --state RELATED,ESTABLISHED -j RETURN
-A WANv6_LOCAL -m comment --comment WANv6_LOCAL-20 -m state --state INVALID -j DROP
-A WANv6_LOCAL -p ipv6-icmp -m comment --comment WANv6_LOCAL-30 -j RETURN
-A WANv6_LOCAL -p udp -m comment --comment WANv6_LOCAL-40 -m udp --sport 547 --dport 546 -j RETURN
-A WANv6_LOCAL -m comment --comment "WANv6_LOCAL-10000 default-action drop" -j LOG --log-prefix "[WANv6_LOCAL-default-D]"
-A WANv6_LOCAL -m comment --comment "WANv6_LOCAL-10000 default-action drop" -j DROP
```

As you can see, both rulesets block all inbound traffic by default unless it is *related* to an existing outbound connection.

###  Create a vlan interface

I need to create a network interface on the router that will be the default gateway for my local IPv6-only network. From the tunnel broker, I received the CIDR `2001:470:1237:1212::/64` for local use, so:

- I've decided to split this up into smaller networks (because a /64 has over 18 *quintillion* available addresses). I'm using `/110` networks in this example, which means I will only ever be able to have 262,146 devices on each network (note that the decision to use a smaller subnet impacts your choices for address autoconfiguration; see [RFC 7421][] for the relevant discussion).

[rfc 7421]: https://www.rfc-editor.org/rfc/rfc7421

- I'm using the first `/110` network for this VLAN, which comprises addresses `2001:470:1237:1212::1` through `2001:470:1237:1212::3:ffff`. I'll use the first address as the router address.

- I've arbitrarily decided to use VLAN id 10 for this purpose.

To create an interface for VLAN id 10 with address `2001:470:1237:1212::1/110`, we use the `set interfaces ... vif` command:

```
set interfaces switch switch0 vif 10 address 2001:470:1237:1212::1/110
```

###  Configure the default IPv6 route

We don't receive [router advertisements][ndp] over the IPv6 tunnel, which means we need to explicitly configure the IPv6 default route. The default gateway will be the "Server IPv6 Address" we received from the tunnel broker.

[ndp]: https://en.wikipedia.org/wiki/Neighbor_Discovery_Protocol

```
set protocol static route6 ::/0 next-hop 2001:470:1236:1212::1
```

### Enable router advertisements

IPv6 systems on our local network will use the [neighbor discovery protocol][ndp] to discover the default gateway for the network. Support for this service is provided by [RADVD][], and we configure it using the `set interfaces ... ipv6 router-advert` command:

[radvd]: https://radvd.litech.org/

```
set interfaces switch switch0 vif 10 ipv6 router-advert send-advert true
set interfaces switch switch0 vif 10 ipv6 router-advert managed-flag true
set interfaces switch switch0 vif 10 ipv6 router-advert prefix ::/110
```

The `managed-flag` setting corresponds to the RADVD `AdvManagedFlag` configuration setting, which instructs clients to use DHCPv6 for address autoconfiguration.

### Configure the DHCPv6 service

While in theory it is possible for clients to assign IPv6 addresses without the use of a DHCP server using [stateless address autoconfiguration][slaac], this requires that we're using a /64 subnet (see e.g. [RFC 7421][]). There is no such limitation when using DHCPv6.

[slaac]: https://en.wikipedia.org/wiki/IPv6_address#Stateless_address_autoconfiguration

```
set service dhcpv6-server shared-network-name VLAN10 subnet 2001:470:1237:1212::/110 address-range start 2001:470:1237:1212::10 stop 2001:470:1237:1212::3:ffff
set service dhcpv6-server shared-network-name VLAN10 subnet 2001:470:1237:1212::/110 name-server 2001:470:1237:1212::1
set service dhcpv6-server shared-network-name VLAN10 subnet 2001:470:1237:1212::/110 domain-search house
set service dhcpv6-server shared-network-name VLAN10 subnet 2001:470:1237:1212::/110 lease-time default 86400
```

Here I'm largely setting things up to mirror the configuration of the IPv4 dhcp server for the `name-server`, `domain-search`, and `lease-time` settings. I'm letting the DHCPv6 server allocate pretty much the entire network range, with the exception of the first 10 addresses.

### Commit the changes

After making the above changes they need to be activated:

```
commit
```

### Verify the configuration

This produces the following interface configuration for `tun0`:

```
13: tun0@NONE: <POINTOPOINT,NOARP,UP,LOWER_UP> mtu 1480 qdisc noqueue state UNKNOWN group default qlen 1000
    link/sit 0.0.0.0 peer 209.51.161.14
    inet6 2001:470:1236:1212::2/64 scope global
       valid_lft forever preferred_lft forever
    inet6 fe80::c0a8:101/64 scope link
       valid_lft forever preferred_lft forever
    inet6 fe80::6c07:49c7/64 scope link
       valid_lft forever preferred_lft forever
```

And for `switch0.10`:

```
ubnt@ubnt:~$ ip addr show switch0.10
14: switch0.10@switch0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    link/ether 78:8a:20:bb:05:db brd ff:ff:ff:ff:ff:ff
    inet6 2001:470:1237:1212::1/110 scope global
       valid_lft forever preferred_lft forever
    inet6 fe80::7a8a:20ff:febb:5db/64 scope link
       valid_lft forever preferred_lft forever
```

And the following route configuration:

```
ubnt@ubnt:~$ ip -6 route | grep -v fe80
2001:470:1236:1212::/64 dev tun0 proto kernel metric 256 pref medium
2001:470:1237:1212::/110 dev switch0.10 proto kernel metric 256 pref medium
default via 2001:470:1236:1212::1 dev tun0 proto zebra metric 1024 pref medium
```

We can confirm things are properly configured by accessing a remote service that reports our ip address:

```
ubnt@ubnt:~$ curl https://api64.ipify.org
2001:470:1236:1212::2
```

## Configure the switch

In my home network, devices in my office connect to a switch, and the switch connects back to the router. I need to configure the switch (an older Netgear M4100-D12G) to pass the VLAN on to the desktop.

### Add vlan 10 to the vlan database with name `ipv6net0`

I start by defining the VLAN in the VLAN database:

```
vlan database
vlan 10
vlan name 10 ipv6net0
exit
```

### Configure vlan 10 as a tagged member of ports 1-10

Next, I configure the switch to pass VLAN 10 as a tagged VLAN on all switch interfaces:

```
configure
interface 0/1-0/10
vlan participation include 10
vlan tagging 10
exit
exit
```

## Configure the desktop

With the above configuration in place, traffic on VLAN 10 will arrive on my Linux desktop (which is connected to the switch we configured in the previous step).  I can use [`nmcli`][nmcli], the [NetworkManager][] CLI, to add a VLAN interface (I'm using [Fedora][] 37, which uses NetworkManager to manage network interface configuration; other distributions may have different tooling).

[fedora]: https://getfedora.org/
[nmcli]: https://developer-old.gnome.org/NetworkManager/stable/nmcli.html
[networkmanager]: https://networkmanager.dev/

The following command will create a *connection* named `vlan10`. Bringing up the connection will create an interface named `vlan10`, configured to receive traffic on VLAN 10 arriving on `eth0`:

```
nmcli con add type vlan con-name vlan10 ifname vlan10 dev eth0 id 10 ipv6.method auto
nmcli con up vlan10
```

This produces the following interface configuration:

```
$ ip addr show vlan10
7972: vlan10@eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    link/ether 2c:f0:5d:c9:12:a9 brd ff:ff:ff:ff:ff:ff
    inet6 2001:470:1237:1212::2:c19a/128 scope global dynamic noprefixroute 
       valid_lft 85860sec preferred_lft 53460sec
    inet6 fe80::ced8:1750:d67c:2ead/64 scope link noprefixroute 
       valid_lft forever preferred_lft forever
```

And the following route configuration:

```
$ ip -6 route show | grep vlan10
2001:470:1237:1212::2:c19a dev vlan10 proto kernel metric 404 pref medium
2001:470:1237:1212::/110 dev vlan10 proto ra metric 404 pref medium
fe80::/64 dev vlan10 proto kernel metric 1024 pref medium
default via fe80::7a8a:20ff:febb:5db dev vlan10 proto ra metric 404 pref medium
```

We can confirm things are properly configured by accessing a remote service that reports our ip address:

```
$ curl https://api64.ipify.org
2001:470:1237:1212::2:c19a
```

Note that unlike access using IPv4, the address visible here is the address assigned to our local interface. There is no NAT happening at the router.

---

Cover image by [Chris Woodford/explainthatstuff.com][chris woodford], licensed  under [CC BY-NC-SA 3.0][].

[chris woodford]: https://www.explainthatstuff.com/chris-woodford.html
[CC BY-NC-SA 3.0]: https://creativecommons.org/licenses/by-nc-sa/3.0/
