---
categories:
- tech
date: '2020-02-15'
filename: 2020-02-15-configuring-open-vswitch-with.md
tags:
- networking
- networkmanager
- nmcli
- openvswitch
title: Configuring Open vSwitch with nmcli
---

I recently acquired a managed switch for my home office in order to segment a few devices off onto their own isolated vlan. As part of this, I want to expose these vlans on my desktop using Open vSwitch (OVS), and I wanted to implement the configuration using NetworkManager rather than either relying on the legacy `/etc/sysconfig/network-scripts` scripts or rolling my own set of services.  These are my notes in case I ever have to do this again.

First, we need the openvswitch plugin for NetworkManager:

```
yum install NetworkManager-ovs
```

Without the plugin, `nmcli` will happily accept all your configuration commands, but you'll get an error when you try to bring an interface up.


## Target configuration

This is what I want when we're done:

```
1e668de8-c2ac-4dd7-9824-95e1cade31ce
    Bridge br-house
        Port "vlan1"
            tag: 1
            Interface "vlan1"
                type: internal
        Port "vlan102"
            tag: 102
            Interface "vlan102"
                type: internal
        Port br-house
            Interface br-house
                type: internal
        Port "eth0"
            Interface "eth0"
                type: system
        Port "vlan101"
            tag: 101
            Interface "vlan101"
                type: internal
    ovs_version: "2.12.0"
```

## NMCLI commands

To create the ovs bridge:

```
nmcli c add type ovs-bridge conn.interface br-house con-name br-house
nmcli c add type ovs-port conn.interface br-house master br-house con-name ovs-port-br-house
nmcli c add type ovs-interface slave-type ovs-port conn.interface br-house master ovs-port-br-house  con-name ovs-if-br-house
```

Unlike `ovs-vsctl`, creating the bridge won't automatically create an interface for you. The two additional commands above get us an actual interface named `br-house` (configured using DHCP, because we didn't explicitly set `ipv4.method` on the interface).

Next, we add `eth0` to the bridge:

```
nmcli c add type ovs-port conn.interface eth0 master br-house con-name ovs-port-eth0
nmcli c add type ethernet conn.interface eth0 master ovs-port-eth0 con-name ovs-if-eth0
```

And finally, we create some ports to expose specific vlans:

```
nmcli c add type ovs-port conn.interface vlan1 master br-house ovs-port.tag 1 con-name ovs-port-vlan1
nmcli c add type ovs-interface slave-type ovs-port conn.interface vlan1 master ovs-port-vlan1 con-name ovs-if-vlan1 ipv4.method static ipv4.address 192.168.7.1/24

nmcli c add type ovs-port conn.interface vlan101 master br-house ovs-port.tag 101 con-name ovs-port-vlan101
nmcli c add type ovs-interface slave-type ovs-port conn.interface vlan101 master ovs-port-vlan101 con-name ovs-if-vlan101 ipv4.method static ipv4.address 192.168.11.1/24

nmcli c add type ovs-port conn.interface vlan102 master br-house ovs-port.tag 102 con-name ovs-port-vlan102
nmcli c add type ovs-interface slave-type ovs-port conn.interface vlan102 master ovs-port-vlan102 con-name ovs-if-vlan102 ipv4.method static ipv4.address 192.168.13.1/24
```