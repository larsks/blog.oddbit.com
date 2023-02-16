---
categories: [tech]
aliases: ["/2014/05/23/solved-open-vswitch-and-persis/"]
title: "Solved: Open vSwitch and persistent MAC addresses"
date: "2014-05-23"
tags:
- openstack
- openvswitch
- networking
---

In my [previous post] I discussed a problem I was having setting a
persistent MAC address on an OVS bridge device.  It looks like the
short answer is, "don't use `ip link set ...`" for this purpose.

You can set the bridge MAC address via `ovs-vsctl` like this:

    ovs-vsctl set bridge br-ex other-config:hwaddr=$MACADDR

So I've updated my `ifconfig-br-ex` to look like this:

    DEVICE=br-ex
    DEVICETYPE=ovs
    TYPE=OVSBridge
    ONBOOT=yes
    OVSBOOTPROTO=dhcp
    OVSDHCPINTERFACES=eth0
    MACADDR=fa:16:3e:ef:91:ec
    OVS_EXTRA="set bridge br-ex other-config:hwaddr=$MACADDR"

The `OVS_EXTRA` parameter gets passed to the `add-br` call like this:

    ovs-vsctl --may-exist add-br br-ex -- set bridge br-ex other-config:hwaddr=$MACADDR

And unlike using `ip link set`, this seems to stick.

[previous post]: /2014/05/23/open-vswitch-and-persistent-ma/

