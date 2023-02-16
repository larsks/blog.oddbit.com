---
categories: [tech]
aliases: ["/2014/05/23/open-vswitch-and-persistent-ma/"]
title: Open vSwitch and persistent MAC addresses
date: "2014-05-23"
tags:
- openvswitch
- networking
- openstack
---

Normally I like to post solutions, but today's post is about a
vexing problem to which I have not been able to find a solution.

This started as a simple attempt to set up external connectivity on
an all-in-one Icehouse install deployed on an OpenStack instance.  I
wanted to add `eth0` to `br-ex` in order to model a typical method for
providing external connectivity, but I ran into a very odd problem:
the system would boot and work fine for a few seconds, but would then
promptly lose network connectivity.

<!-- more -->

The immediate cause was that the MAC address on `br-ex` was changing.
I was setting the MAC explicitly in the configuration file:

    # cat ifcfg-br-ex
    DEVICE=br-ex
    DEVICETYPE=ovs
    TYPE=OVSBridge
    ONBOOT=yes
    OVSBOOTPROTO=dhcp
    OVSDHCPINTERFACES=eth0
    MACADDR=fa:16:3e:ef:91:ec

This was required in this case in order to make the MAC-address
filters on the host happy.  When booting an instance, Neutron sets up
a rule like this:

    -A neutron-openvswi-s55439d7d-a -s 10.0.0.8/32 -m mac --mac-source FA:16:3E:EF:91:EC -j RETURN
    -A neutron-openvswi-s55439d7d-a -j DROP

But things quickly got weird.  Some testing demonstrated that the MAC
address was changing when starting `neutron-openvswitch-agent`, but a
thorough inspection of the code didn't yield any obvious culprits for
this behavior.

I liberally sprinkled the agent with the following (incrementing the
argument to `echo` each time to uniquely identify each message):

    os.system('echo 1 >> /tmp/ovs.log; ip link show dev br-ex >> /tmp/ovs.log')

It turns out that the MAC address on `br-ex` was changing...when
Neutron was deleting a port on `br-int`.  Specifically, at [this
line][] in `ovs_neutron_agent.py`:

[this line]: https://github.com/openstack/neutron/blob/423ca756af10e10398636d6d34a7594a4fd4bc87/neutron/plugins/openvswitch/agent/ovs_neutron_agent.py#L909

    self.int_br.delete_port(int_veth_name)

After some additional testing, it turns out that just about *any* OVS
operation causes an explicit MAC address to disappear.  For example,
create a new OVS bridge:

    # ovs-vsctl add-br br-test0
    # ip link show dev br-test0
    9: br-test0: <BROADCAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN 
        link/ether ba:cb:48:b9:6a:43 brd ff:ff:ff:ff:ff:ff

Then set the MAC address:

    # ip link set br-test0 addr c0:ff:ee:ee:ff:0c
    # ip link show br-test0
    8: br-test0: <BROADCAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN 
        link/ether c0:ff:ee:ee:ff:0c brd ff:ff:ff:ff:ff:ff

Now create a new bridge:

    # ovs-vsctl add-br br-test1

And inspect the MAC address on the first bridge:

    # ip link show dev br-test0
    9: br-test0: <BROADCAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN 
        link/ether ba:cb:48:b9:6a:43 brd ff:ff:ff:ff:ff:ff

In other words, creating a new bridge caused the MAC address on
`br-ex` to revert.  Other operations (e.g., deleting a port on an
unrelated switch) will cause the same behavior.

I've seen this behavior on both versions `1.11.0` and `2.0.1`.

So far everyone I've asked about this behavior has been stumped.  If I
am able to figure out what's going on I will update this post.  Thanks
for reading!

