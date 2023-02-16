---
categories: [tech]
aliases: ["/2014/05/20/firewalld-and-openstack/"]
title: Firewalld, NetworkManager, and OpenStack
date: "2014-05-20"
tags:
- openstack
- networking
- firewalld
- NetworkManager
---

These are my notes on making OpenStack play well with [firewalld][]
and [NetworkManager][].

NetworkManager
--------------

By default, NetworkManager attempts to start a DHCP client on every
new available interface.  Since booting a single instance in OpenStack
can result in the creation of several virtual interfaces, this results
in a lot of:

    May 19 11:58:24 pk115wp-lkellogg NetworkManager[1357]: <info>
      Activation (qvb512640bd-ee) starting connection 'Wired connection 2'

You can disable this behavior by adding the following to
`/etc/NetworkManager/NetworkManager.conf`:

    [main]
    no-auto-default=*

From `NetworkManager.conf(5)`:

>  Comma-separated list of devices for which NetworkManager shouldn't
>  create default wired connection (Auto eth0). By default,
>  NetworkManager creates a temporary wired connection for any
>  Ethernet device that is managed and doesn't have a connection
>  configured. List a device in this option to inhibit creating the
>  default connection for the device. May have the special value * to
>  apply to all devices.

FirewallD
---------

[FirewallD][] is the firewall manager recently introduced in Fedora
(and soon to be appearing in RHEL 7).

I start by creating a new zone named `openstack` by creating the file
`/etc/firewalld/zones/openstack.xml` with the following content:

    <?xml version="1.0" encoding="utf-8"?>
    <zone>
      <short>OpenStack</short>
      <description>For OpenStack services</description>
    </zone>

After populating this file, you need to run `firewall-cmd --reload`
to make the zone available.  Note that if you're already running
OpenStack this will hose any rules set up by Neutron or Nova, so
you'll probably want to restart those services:

    # openstack-service restart nova neutron

I then add `br-ex` to this zone, where `br-ex` is the OVS bridge my
OpenStack environment uses for external connectivity:

    # echo ZONE=openstack >> /etc/sysconfig/network-scripts/ifcfg-br-ex

I run a `dnsmasq` instance on my laptop to which I expect OpenStack
instances to connect, so I need to add the `dns` service to this zone:

    # firewall-cmd --zone openstack --add-service dns
    # firewall-cmd --zone openstack --add-service dns --permanent

I'm running `firewall-cmd` twice here: the first time modifies the
currently running configuration, while the second makes the change
persistent across reboots.

On my laptop, I handle external connectivity through NAT rather than
placing floating ips on a "real" network.  To make this work, I add my
ethernet and wireless interfaces to the `external` zone, which already
has ip masquerading enabled, by adding a `ZONE` directive to the
appropriate interface configuration file:

    # echo ZONE=external >> /etc/sysconfig/network-scripts/ifcfg-em1

After a reboot, things look like this:

    # firewall-cmd --get-active-zones
    openstack
      interfaces: br-ex
    external
      interfaces: em1
    public
      interfaces: int-br-ex phy-br-ex qvb58cc67ca-06 qvo58cc67ca-06
    # firewall-cmd --zone openstack --list-services
    dns

[firewalld]: https://fedoraproject.org/wiki/FirewallD
[networkmanager]: https://wiki.gnome.org/Projects/NetworkManager

