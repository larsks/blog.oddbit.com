---
aliases:
- /2015/08/13/provider-external-networks-details/
- /post/2015-08-13-provider-external-networks-details
categories:
- tech
date: '2015-08-13'
tags:
- openstack
- neutron
- openvswitch
- networking
title: Provider external networks (in an appropriate amount of detail)
---

In [Quantum in Too Much Detail][1], I discussed the architecture of a
Neutron deployment in detail.  Since that article was published,
Neutron gained the ability to handle multiple external networks with a
single L3 agent.  While I [wrote about that][2] back in 2014, I
covered the configuration side of it in much more detail than I
discussed the underlying network architecture.  This post addresses
the architecture side.

[1]: {{< ref "quantum-in-too-much-detail" >}}
[2]: {{< ref "multiple-external-networks-wit" >}}

## The players

This document describes the architecture that results from a
particular OpenStack configuration, specifically:

- Neutron networking using VXLAN or GRE tunnels;
- A dedicated network controller;
- Two external networks

## The lay of the land

This is a simplified architecture diagram of the network connectivity
in this scenario:

{{< ref
src="neutron-provider-external.svg"
link="neutron-provider-external.svg"
width="600"
>}}

Everything on the compute hosts is identical to [my previous
article][1], so I will only be discussing the network host here.

For the purposes of this article, we have two external networks and
two internal networks defined:

    $ neutron net-list
    +--------------------------------------+-----------+----------...------------------+
    | id                                   | name      | subnets  ...                  |
    +--------------------------------------+-----------+----------...------------------+
    | 6f0a5622-4d2b-4e4d-b34a-09b70cacf3f1 | net1      | beb767f8-... 192.168.101.0/24 |
    | 972f2853-2ba6-474d-a4be-a400d4e3dc97 | net2      | f6d0ca0f-... 192.168.102.0/24 |
    | 12136507-9bbe-406f-b68b-151d2a78582b | external2 | 106db3d6-... 172.24.5.224/28  |
    | 973a6eb3-eaf8-4697-b90b-b30315b0e05d | external1 | fe8e8193-... 172.24.4.224/28  |
    +--------------------------------------+-----------+----------...------------------+

And two routers:

    $ neutron router-list
    +--------------------------------------+---------+-----------------------...-------------------+...
    | id                                   | name    | external_gateway_info ...                   |...
    +--------------------------------------+---------+-----------------------...-------------------+...
    | 1b19e179-5d67-4d80-8449-bab42119a4c5 | router2 | {"network_id": "121365... "172.24.5.226"}]} |...
    | e2117de3-58ca-420d-9ac6-c4eccf5e7a53 | router1 | {"network_id": "973a6e... "172.24.4.227"}]} |...
    +--------------------------------------+---------+-----------------------...-------------------+...

And our logical connectivity is:

    +---------+    +----------+    +-------------+
    |         |    |          |    |             |
    |  net1   +----> router1  +---->  external1  |
    |         |    |          |    |             |
    +---------+    +----------+    +-------------+

    +---------+    +----------+    +-------------+
    |         |    |          |    |             |
    |  net2   +----> router2  +---->  external2  |
    |         |    |          |    |             |
    +---------+    +----------+    +-------------+


## Router attachments to integration bridge

In the [legacy model][1], in which an L3 agent supported a single
external network, the `qrouter-...` namespaces that implement Neutron
routers were attached to both the integration bridge `br-int` and the
external network bridge (the `external_network_bridge` configuration
option from your `l3_agent.ini`, often named `br-ex`).

In the provider network model, *both* interfaces in a `qrouter`
namespace are attached to the integration bridge.  For the
configuration we've described above, the configuration of the
integration bridge ends up looking something like:

    Bridge br-int
        fail_mode: secure
        Port "qvoc532d46c-33"
            tag: 3
            Interface "qvoc532d46c-33"
        Port br-int
            Interface br-int
                type: internal
        Port "qg-09e9da38-fb"
            tag: 4
            Interface "qg-09e9da38-fb"
                type: internal
        Port "qvo3ccea690-c2"
            tag: 2
            Interface "qvo3ccea690-c2"
        Port "int-br-ex2"
            Interface "int-br-ex2"
                type: patch
                options: {peer="phy-br-ex2"}
        Port "tapd2ff89e7-16"
            tag: 2
            Interface "tapd2ff89e7-16"
                type: internal
        Port patch-tun
            Interface patch-tun
                type: patch
                options: {peer=patch-int}
        Port "int-br-ex1"
            Interface "int-br-ex1"
                type: patch
                options: {peer="phy-br-ex1"}
        Port "qr-affdbcee-5c"
            tag: 3
            Interface "qr-affdbcee-5c"
                type: internal
        Port "qr-b37877cd-42"
            tag: 2
            Interface "qr-b37877cd-42"
                type: internal
        Port "qg-19250d3f-5c"
            tag: 1
            Interface "qg-19250d3f-5c"
                type: internal
        Port "tap0881edf5-e5"
            tag: 3
            Interface "tap0881edf5-e5"
                type: internal

The `qr-...` interface on each router is attached to an internal
network.  The VLAN tag associated with this interface is whatever VLAN
Neutron has selected internally for the private network.  In the above
output, these ports are on the network named `net1`:

    Port "qr-affdbcee-5c"
        tag: 3
        Interface "qr-affdbcee-5c"
            type: internal
    Port "tap0881edf5-e5"
        tag: 3
        Interface "tap0881edf5-e5"
            type: internal

Where `qr-affdbcee-5c` is `router1`'s interface on that network, and
`tap0881edf5-e5` is the port attached to a `dhcp-...` namespace.  The
same router is attached to the `external1` network; this attachment is
represented by:

    Port "qg-09e9da38-fb"
        tag: 4
        Interface "qg-09e9da38-fb"
            type: internal

The external bridges are connected to the integration bridge using OVS
"patch" interfaces (the `int-br-ex1` on the integration bridge and the
`phy-br-ex1` interface on the `br-ex1`).

## From here to there

Connectivity between the `qg-...` interface and the appropriate
external bridge (`br-ex1` in this case) happens due to the VLAN tag
assigned on egress by the `qg-...` interface and the following
OpenFlow rules associated with `br-ex1`:

    # ovs-ofctl dump-flows br-ex1
    NXST_FLOW reply (xid=0x4):
     cookie=0x0, duration=794.876s, table=0, n_packets=0, n_bytes=0, idle_age=794, priority=1 actions=NORMAL
     cookie=0x0, duration=785.833s, table=0, n_packets=0, n_bytes=0, idle_age=785, priority=4,in_port=3,dl_vlan=4 actions=strip_vlan,NORMAL
     cookie=0x0, duration=792.945s, table=0, n_packets=24, n_bytes=1896, idle_age=698, priority=2,in_port=3 actions=drop

Each of these rules contains some state information (like the
packet/byte counts), some conditions (like
`priority=4,in_port=3,dl_vlan=4`) and one or more actions (like
`actions=strip_vlan,NORMAL`).  So, the second rule there matches
packets associated with VLAN tag 4 and strips the VLAN tag (after
which the packet is delivered to any physical interfaces that are
attached to this OVS bridge).

Putting this all together:

1. An outbound packet from a Nova server running on a compute node
   enters via `br-tun` (**H**)

1. Flow rules on `br-tun` translate the tunnel id into an internal
   VLAN tag.

1.  The packet gets delivered to the `qr-...` interface of the
    appropriate router. (**O**)

1. The packet exits the `qg-...` interface of the router (where it
   is assigned the VLAN tag associated with the external network).
   (**N**)

1. The packet is delivered to the external bridge, where a flow rule
   strip the VLAN tag. (**P**)

1. The packet is sent out the physical interface associated with the
   bridge.

## For the sake of completeness

The second private network, `net2`, is attached to `router2` on the
`qr-b37877cd-42` interface.  It exits on the `qg-19250d3f-5c`
interface, where packets will be assigned to VLAN 1:

    Port "qr-b37877cd-42"
        tag: 2
        Interface "qr-b37877cd-42"
            type: internal
    Port "qg-19250d3f-5c"
        tag: 1
        Interface "qg-19250d3f-5c"
            type: internal

The network interface configuration in the associated router namespace
looks like this:

    # ip netns exec qrouter-1b19e179-5d67-4d80-8449-bab42119a4c5 ip a
    30: qg-19250d3f-5c: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN 
        link/ether fa:16:3e:01:e9:e3 brd ff:ff:ff:ff:ff:ff
        inet 172.24.5.226/28 brd 172.24.5.239 scope global qg-19250d3f-5c
           valid_lft forever preferred_lft forever
        inet6 fe80::f816:3eff:fe01:e9e3/64 scope link 
           valid_lft forever preferred_lft forever
    37: qr-b37877cd-42: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN 
        link/ether fa:16:3e:4c:6c:f2 brd ff:ff:ff:ff:ff:ff
        inet 192.168.102.1/24 brd 192.168.102.255 scope global qr-b37877cd-42
           valid_lft forever preferred_lft forever
        inet6 fe80::f816:3eff:fe4c:6cf2/64 scope link 
           valid_lft forever preferred_lft forever

OpenFlow rules attached to `br-ex2` will match these packets:

    # ovs-ofctl dump-flows br-ex2
    NXST_FLOW reply (xid=0x4):
     cookie=0x0, duration=3841.678s, table=0, n_packets=0, n_bytes=0, idle_age=3841, priority=1 actions=NORMAL
     cookie=0x0, duration=3831.396s, table=0, n_packets=0, n_bytes=0, idle_age=3831, priority=4,in_port=3,dl_vlan=1 actions=strip_vlan,NORMAL
     cookie=0x0, duration=3840.085s, table=0, n_packets=26, n_bytes=1980, idle_age=3742, priority=2,in_port=3 actions=drop

We can see that the second rule here will patch traffic on VLAN 1
(`priority=4,in_port=3,dl_vlan=1`) and strip the VLAN tag, after which
the packet will be delivered to any other interfaces attached to this
bridge.
