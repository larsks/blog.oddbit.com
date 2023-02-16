---
categories:
- tech
date: '2019-12-19'
filename: 2019-12-19-ovn-and-dhcp.md
tags:
- openstack
- ovn
- openvswitch
- networking
title: 'OVN and DHCP: A minimal example'
toc: true
---

# Introduction

A long time ago, I wrote an article [all about OpenStack Neutron][neutron] (which at that time was called Quantum). That served as an excellent reference for a number of years, but if you've deployed a recent version of OpenStack you may have noticed that the network architecture looks completely different. The network namespaces previously used to implement routers and dhcp servers are gone (along with iptables rules and other features), and have been replaced by OVN ("Open Virtual Network"). What is OVN? How does it work? In this article, I'd like to explore a minimal OVN installation to help answer these questions.

[neutron]: {{< ref "quantum-in-too-much-detail" >}}

## Goals

We're going to create a single OVN logical switch to which we will attach a few ports. We will demonstrate how we can realize a port on a physical node and configure it using DHCP, using a virtual DHCP server provided by OVN.

## So what is OVN anyway?

If you're just getting started with OVN, you'll find that's a hard question to answer: there is no dedicated OVN website; there's no OVN landing page at <http://openvswitch.org>; in fact, there's really no documentation for OVN at all other than the man pages. The only high-level description you'll find comes from the `ovn-architecture(7)` man page:

> OVN,  the  Open Virtual Network, is a system to support virtual network
> abstraction. OVN complements the existing capabilities of  OVS  to  add
> native support for virtual network abstractions, such as virtual L2 and L3
> overlays and security groups.

Where Open vSwitch (OVS) provides a virtual switch on a single host, OVN extends this abstraction to span multiple hosts. You can create virtual switches that span many physical nodes, and OVN will take care of creating overlay networks to support this abstraction. While OVS is primarily just a layer 2 device, OVN also operates at layer 3: you can create virtual routers to connect your virtual networks as well a variety of access control mechanisms such as security groups and ACLs.

## Requirements

You're going to need a recent version of OVN. Packages are available for [most major distributions][packages]. I used [Fedora 31][] for my testing, which includes OVS and OVN version 2.12.0. You can of course also [install from source][ovsinstall].

This post assumes that you are logged in to your system as the `root` user. Most of the commands require root access in order to function correctly.

[ovsinstall]: http://docs.openvswitch.org/en/latest/intro/install/
[packages]: http://docs.openvswitch.org/en/latest/intro/install/distributions/
[fedora 31]: https://getfedora.org/

## Concepts

OVN operates with a pair of databases. The _Northbound_ database contains the _logical_ structure of your networks: this is where you define switches, routers, ports, and so on.

The _Southbound_ database is concerned with the _physical_ structure of your network. This database maintains information about which ports are realized on which hosts.

The [`ovn-northd`][ovn-northd] service "translates  the logical network configuration in terms of conventional network concepts, taken from the OVN  North‐ bound  Database,  into  logical datapath flows in the OVN Southbound Database below it." ([ovn-architecture(7)][])

The [`ovn-controller`][ovn-controller] service running on each host connects to the Southbound database and is responsible for configuring OVS as instructed by the database configuration.

[ovn-architecture(7)]: http://www.openvswitch.org/support/dist-docs/ovn-architecture.7.html
[ovn-northd]: http://www.openvswitch.org/support/dist-docs/ovn-northd.8.html
[ovn-controller]: http://www.openvswitch.org/support/dist-docs/ovn-controller.8.html

## Test environment

This article assumes a test environment with three nodes running Fedora 31. All nodes have a single interface connecting to a shared layer 2 network:

| Name | MAC address       | IP address      |
|------|-------------------|-----------------|
| ovn0 | de:ca:ff:00:00:64 | 192.168.122.100 |
| ovn1 | de:ca:ff:00:00:65 | 192.168.122.101 |
| ovn2 | de:ca:ff:00:00:66 | 192.168.122.102 |

# Setting up OVN

## Initial configuration steps

Our first step will be to activate `openvswitch` and `ovn-controller` on all of the nodes in our test environment. On all nodes, run the following command:

```
systemctl enable --now openvswitch ovn-controller
```

The `--now` flag causes `systemd` to start the service as well as enabling it in future boots.

By default, OVN manages an `openvswitch` bridge named `br-int` (for "integration"). We'll need to create this on all of our nodes. On all nodes, run:

```
ovs-vsctl add-br br-int
```


## Configuring the controller

We will designate the node `ovn0` as our controller (which simply means "this node will run `ovn-northd`). The first thing we need to do is enable the `ovn-northd` service. On node `ovn0`, run:

```
systemctl enable --now ovn-northd
```

In addition to starting the `ovn-northd` service itself, this will also starts two instances of [`ovsdb-server`][ovsdb-server]: one serving the Northbound database, listening on `/run/ovn/ovnnb_db.sock`, and the second for the Southbound database, listening on `/run/ovn/ovnsb_db.sock`. In order for the `ovn-controller` service on the other nodes to connect to the Southbound database, we will need to configure that instance of `ovsdb-server` to listen for tcp connections.  We can do that using the `ovn-sbctl set-connection` command:

```
ovn-sbctl set-connection ptcp:6642
```

The `ptcp` in the above setting means "passive tcp", which means "listen on port 6642 for connections". After running the above command, we see that there is now an `ovsdb-server` instance listening on port 6642:

```
[root@ovn0 ~]# ss -tlnp | grep 6642
LISTEN    0         10                 0.0.0.0:6642             0.0.0.0:*        users:(("ovsdb-server",pid=1798,fd=21))
```

[ovsdb-server]: http://www.openvswitch.org/support/dist-docs/ovsdb-server.1.html

## Connecting nodes to the controller

Now that we have our controller configured, we have to connect the `ovn-controller` service on our nodes to the Southbound database. We do this by creating several entries in the `external_ids` column of the OVS `open_vswitch` database on each host:

- `ovn-remote` -- this is the address of the controller
- `ovn-encap-ip` -- this is the local address that will be used for tunnel endpoints
- `ovn-encap-type` -- the encapsulation mechanism to use for tunnels
- `system-id` -- a unique identifier for the local host

On all nodes, run the following command:

```
ovs-vsctl set open_vswitch .  \
  external_ids:ovn-remote=tcp:192.168.122.100:6642 \
  external_ids:ovn-encap-ip=$(ip addr show eth0 | awk '$1 == "inet" {print $2}' | cut -f1 -d/) \
  external_ids:ovn-encap-type=geneve \
  external_ids:system-id=$(hostname)
```

This points `ovn-remote` at the address of the controller, sets `ovn-encap-ip` to the address of `eth0` on the local host, sets `systemd-id` to the local hostname, and selects [geneve][] encapsulation for tunnels (see [this post][russelbryant-ovn-geneve-vs-vxlan] for information on why OVN prefers Geneve encapsulation).

We can verify these settings by using the `ovs-vsctl list` command:

```
[root@ovn1 ~]# ovs-vsctl --columns external_ids list open_vswitch
external_ids        : {hostname="ovn1.virt", ovn-encap-ip="192.168.122.101", ovn-encap-type=geneve, ovn-remote="192.168.122.100", rundir="/var/run/openvswitch", system-id="ovn1"}
```

[geneve]: https://tools.ietf.org/html/draft-ietf-nvo3-geneve-08
[russelbryant-ovn-geneve-vs-vxlan]: https://blog.russellbryant.net/2017/05/30/ovn-geneve-vs-vxlan-does-it-matter/

After running the above commands, each node should now have tunnels interfaces connecting to the other nodes in the test environment. For example, running `ovs-vsctl show` on node `ovn1` looks like this:

```
f0087676-7f93-419c-9da0-32321d2d3668
    Bridge br-int
        fail_mode: secure
        Port "ovn-ovn0-0"
            Interface "ovn-ovn0-0"
                type: geneve
                options: {csum="true", key=flow, remote_ip="192.168.122.100"}
        Port br-int
            Interface br-int
                type: internal
        Port "ovn-ovn2-0"
            Interface "ovn-ovn2-0"
                type: geneve
                options: {csum="true", key=flow, remote_ip="192.168.122.102"}
    ovs_version: "2.12.0"
```

Due to what appears to be [some sort of race condition in OVN][bug-geneve], you may not see the geneve tunnels in the `ovs-vsctl show` output.  If this is the case, restart `ovn-controller` on all your ovn nodes:

```
systemctl restart ovn-controller
```

The issue with the geneve tunnels appears to be resolved by [this patch][], which will hopefully land in OVN in the near future.

[bug-geneve]: https://mail.openvswitch.org/pipermail/ovs-discuss/2020-January/049692.html
[this patch]: https://patchwork.ozlabs.org/patch/1222380/


# Creating a virtual network

Now that we have a functioning OVN environment, we're ready to create our virtual network.

## Create a logical switch

We'll start by creating a logical switch, which we will call `net0`. We create that using the `ovn-nbctl ls-add` command. Run the following on `ovn0`:

```
ovn-nbctl ls-add net0
```

After running the above command, the output of `ovn-nbctl show` will look something like this:

```
[root@ovn0 ~]# ovn-nbctl show
switch d8d96fb2-e1e7-469d-8c72-b7e891fb16ba (net0)
```

Next, we need to set some configuration options on the switch that will be used to set the range from which we allocate addresses via DHCP.  We're going to have OVN manage the `10.0.0.0/24` network, which means we need to set `other_config:subnet` to `10.0.0.0/24`. I generally like to reserve some addresses from the DHCP range to use for static allocations, so I have also set `other_config:exclude_ips` to `10.0.0.1..10.0.0.10`. This means that DHCP allocations will come from the range `10.0.0.11` - `10.0.0.254`.

To apply these settings, run the following commands on `ovn0`:

```
ovn-nbctl set logical_switch net0 \
  other_config:subnet="10.0.0.0/24" \
  other_config:exclude_ips="10.0.0.1..10.0.0.10"
```

## Create DHCP options

Each port that we want to configure using DHCP needs to be associated with a set of DHCP options. We accomplish this by creating a new entry in the Northbound `dhcp_options` table, and then set the `dhcp_options` column of the port to the id of the object we created in the `dhcp_options` table.

Looking at [the source][northd-source], there are three required options that must be set in order for DHCP to operate:

- `server_id` -- the ip address of the virtual dhcp server
- `server_mac` -- the MAC address of the virtual dhcp server
- `lease_time` -- the lifetime of DHCP leases

While not actually required, we can also set the `router` key to provide information about the default gateway. We're not going to make use of it in this example, but in practice you will probably want to set the `router` option.

We also need to set the CIDR range that will be served by the DHCP server.

[northd-source]: https://github.com/ovn-org/ovn/blob/master/northd/ovn-northd.c#L4113

We can create the appropriate options using the `ovn-nbctl dhcp-options-create` command. Run the following on `ovn0`:

```
ovn-nbctl dhcp-options-create 10.0.0.0/24
```

Despite the name of that command, it doesn't actually let us set DHCP options. For that, we need to first look up the uuid of our newly created entry in the `dhcp_options` table. Let's store that in the `CIDR_UUID` variable, which we will use in a few places in the remainder of this post:

```
CIDR_UUID=$(ovn-nbctl --bare --columns=_uuid find dhcp_options cidr="10.0.0.0/24")
```

With that uuid in hand, we can now set the required options:

```
ovn-nbctl dhcp-options-set-options ${CIDR_UUID} \
  lease_time=3600 \
  router=10.0.0.1 \
  server_id=10.0.0.1 \
  server_mac=c0:ff:ee:00:00:01
```

We can use the database `list` command to inspect the `dhcp_options` table to verify that things look as we expect:

```
[root@ovn0 ~]# ovn-nbctl list dhcp_options
_uuid               : f8a6abc5-b8e4-4209-8809-b95435b4d48b
cidr                : "10.0.0.0/24"
external_ids        : {lease_time="3600", router="10.0.0.1", server_id="10.0.0.1", server_mac="c0:ff:ee:00:00:01"}
options             : {}
```

Instead of using the `dhcp-options-create` command, as we did in this section, we could instead have used the database `create` command. The quoting requirements for that command are a little more complex, but unlike the `dhcp-options-create` command the `create` command returns the id of the row it creates. This can be useful if you're using the command as part of a script. The equivalent `create` command would look like:

```
CIDR_UUID=$(ovn-nbctl create dhcp_options \
  cidr=10.0.0.0/24 \
  options='"lease_time"="3600" "router"="10.0.0.1" "server_id"="10.0.0.1" "server_mac"="c0:ff:ee:00:00:01"')
```

## Create logical ports

Let's add the following three logical ports to the switch:

| Name  | MAC Address       |
|-------|-------------------|
| port1 | c0:ff:ee:00:00:11 |
| port2 | c0:ff:ee:00:00:12 |
| port3 | c0:ff:ee:00:00:13 |

For each port, we'll need to run three commands. First, we create the port on the switch:

```
ovn-nbctl lsp-add net0 port1
```

Next, we set the port addresses. For this example, I'm using static MAC addresses and dynamic (assigned by DHCP) IP addresses, so the command will look like:

```
ovn-nbctl lsp-set-addresses port1 "c0:ff:ee:00:00:11 dynamic"
```

If you want OVN to set MAC addresses for the ports as well, you would instead run:

```
ovn-nbctl lsp-set-addresses port1 "dynamic"
```

Finally, we associate the port with the DHCP options we created in the previous section:

```
ovn-nbctl lsp-set-dhcpv4-options port1 $CIDR_UUID
```

Repeat the above sequence for `port2` and `port3`:

```
ovn-nbctl lsp-add net0 port2
ovn-nbctl lsp-set-addresses port2 "c0:ff:ee:00:00:12 dynamic"
ovn-nbctl lsp-set-dhcpv4-options port2 $CIDR_UUID
ovn-nbctl lsp-add net0 port3
ovn-nbctl lsp-set-addresses port3 "c0:ff:ee:00:00:13 dynamic"
ovn-nbctl lsp-set-dhcpv4-options port3 $CIDR_UUID
```

When you're done, `ovn-nbctl show` should return output similar to the following:

```
switch 3c03342f-f762-410b-9f4e-572d266c8ff7 (net0)
    port port2
        addresses: ["c0:ff:ee:00:00:12 dynamic"]
    port port3
        addresses: ["c0:ff:ee:00:00:13 dynamic"]
    port port1
        addresses: ["c0:ff:ee:00:00:11 dynamic"]
```

We can see additional details using the database command `ovn-nbctl list logical_switch_port`.  The entry for `port1` might look like this:

```
_uuid               : 8ad6a4c0-4c7b-4817-bf13-8e7b1a86bab1
addresses           : ["c0:ff:ee:00:00:11 dynamic"]
dhcpv4_options      : f8a6abc5-b8e4-4209-8809-b95435b4d48b
dhcpv6_options      : []
dynamic_addresses   : "c0:ff:ee:00:00:11 10.0.0.11"
enabled             : []
external_ids        : {}
ha_chassis_group    : []
name                : port1
options             : {}
parent_name         : []
port_security       : []
tag                 : []
tag_request         : []
type                : ""
up                  : false
```

Looking at the `dynamic_addresses` column we can see that `port1` has been assigned the ip address `10.0.0.11`. We can see the assigned addresses for all of our ports like this:

```
[root@ovn0 ~]# ovn-nbctl --columns dynamic_addresses list logical_switch_port
dynamic_addresses   : "c0:ff:ee:00:00:13 10.0.0.13"

dynamic_addresses   : "c0:ff:ee:00:00:11 10.0.0.11"

dynamic_addresses   : "c0:ff:ee:00:00:12 10.0.0.12"
```



## Simulating a DHCP request with ovn-trace

At this point, we have a functioning switch, although we haven't actually realized the ports anywhere yet. This is the perfect time to introduce the `ovn-trace` tool, which can be used to simulate how your OVN network will handle a packet of data.

We can show how OVN will respond to a DHCP `DISCOVER` message with the following command:

```
ovn-trace --summary net0 '
  inport=="port1" &&
  eth.src==c0:ff:ee:00:00:11 &&
  ip4.src==0.0.0.0 &&
  ip.ttl==1 &&
  ip4.dst==255.255.255.255 &&
  udp.src==68 &&
  udp.dst==67'
```

The above command simulates a packet originating on `port1` with the appropriate MAC address (`eth.src`, `c0:ff:ee:00:00:11`) and a source address (`ip4.src`) of `0.0.0.0` (port 68 (`udp.src`)), targeting (`ip4.dst`) the broadcast address `255.255.255.255` (port 67 (`udp.dst`)).

Assuming everything is functioning correctly, this should produce the following output:

```
# udp,reg14=0x2,vlan_tci=0x0000,dl_src=c0:ff:ee:00:00:11,dl_dst=c0:ff:ee:00:00:01,nw_src=0.0.0.0,nw_dst=255.255.255.255,nw_tos=0,nw_ecn=0,nw_ttl=1,tp_src=68,tp_dst=67
ingress(dp="net0", inport="port1") {
    next;
    reg0[3] = put_dhcp_opts(offerip = 10.0.0.11, lease_time = 3600, netmask = 255.255.255.0, router = 10.0.0.1, server_id = 10.0.0.1);
    /* We assume that this packet is DHCPDISCOVER or DHCPREQUEST. */;
    next;
    eth.dst = eth.src;
    eth.src = c0:ff:ee:00:00:01;
    ip4.dst = 10.0.0.11;
    ip4.src = 10.0.0.1;
    udp.src = 67;
    udp.dst = 68;
    outport = inport;
    flags.loopback = 1;
    output;
    egress(dp="net0", inport="port1", outport="port1") {
        next;
        output;
        /* output to "port1", type "" */;
    };
};
```

In the above output, you can see that OVN is filling in the details of the DHCP lease (that's the `put_dhcp_options` command), and then sending the packet back out `port1` with the ethernet source and destination addresses reversed (so that the destination address is now the MAC address of `port1`).

It looks like everything is working in theory. Let's attach some actual network interfaces and see what happens!

# Attaching network interfaces

In this section, we will attach network interfaces to our logical switch and demonstrate that they can be properly configured using DHCP.

## Create an OVS port

On host `ovn1`, let's create port `port1`. We'll want to ensure that (a) the MAC address of this port matches the MAC address we configured earlier (`c0:ff:ee:00:00:11`), and we need to make sure that the `iface-id` external id matches the port name we registered in the Northbound database. We can do that with the following command:

```
ovs-vsctl add-port br-int port1 -- \
  set interface port1 \
    type=internal \
    mac='["c0:ff:ee:00:00:11"]' \
    external_ids:iface-id=port1
```

After running this command, running `ovs-vsctl show` on `ovn1` should produce:

```
[root@ovn1 ~]# ovs-vsctl show
f359ad7a-5fcd-49b3-8557-e61be3a0b130
    Bridge br-int
        fail_mode: secure
        Port br-int
            Interface br-int
                type: internal
        Port "port1"
            Interface "port1"
                type: internal
        Port "ovn-ovn2-0"
            Interface "ovn-ovn2-0"
                type: geneve
                options: {csum="true", key=flow, remote_ip="192.168.122.102"}
        Port "ovn-ovn0-0"
            Interface "ovn-ovn0-0"
                type: geneve
                options: {csum="true", key=flow, remote_ip="192.168.122.100"}
    ovs_version: "2.12.0"
```

Furthermore, OVN should also be aware of this port. If we run `ovn-sbctl show` on `ovn0`, we see a binding for host `ovn1` (look for the `Port_Binding port1` line under `Chassis ovn1`):

```
[root@ovn0 ~]# ovn-sbctl show
Chassis ovn0
    hostname: ovn0.virt
    Encap geneve
        ip: "192.168.122.100"
        options: {csum="true"}
Chassis ovn1
    hostname: ovn1.virt
    Encap geneve
        ip: "192.168.122.101"
        options: {csum="true"}
    Port_Binding port1
Chassis ovn2
    hostname: ovn2.virt
    Encap geneve
        ip: "192.168.122.102"
        options: {csum="true"}
```

## Configure the port using DHCP

We can now try to configure this interface with DHCP. Let's first move the interface into a network namespace; this means we don't need to worry about messing up routing on the host. We'll create a namespace named `vm1` and make `port1` part of that namespace:

```
ip netns add vm1
ip link set netns vm1 port1
ip -n vm1 addr add 127.0.0.1/8 dev lo
ip -n vm1 link set lo up
```

We can now configure the interface using DHCP by running the `dhclient` command:

```
ip netns exec vm1 dhclient -v -i port1 --no-pid
```


After `dhclient` goes to the background, we see that it was able to successfully request an address:

```
[root@ovn1 ~]# ip netns exec vm1 dhclient -v -i port1 --no-pid
Internet Systems Consortium DHCP Client 4.4.1
Copyright 2004-2018 Internet Systems Consortium.
All rights reserved.
For info, please visit https://www.isc.org/software/dhcp/

Listening on LPF/port1/c0:ff:ee:00:00:11
Sending on   LPF/port1/c0:ff:ee:00:00:11
Sending on   Socket/fallback
Created duid "\000\004\344J\012\236\007\033AF\261\354\246\273\206\011\226g".
DHCPDISCOVER on port1 to 255.255.255.255 port 67 interval 7 (xid=0xffc0820a)
DHCPOFFER of 10.0.0.11 from 10.0.0.1
DHCPREQUEST for 10.0.0.11 on port1 to 255.255.255.255 port 67 (xid=0xffc0820a)
DHCPACK of 10.0.0.11 from 10.0.0.1 (xid=0xffc0820a)
bound to 10.0.0.11 -- renewal in 1378 seconds.
```

And it has correctly configured the interface:

```
[root@ovn1 ~]# ip netns exec vm1 ip addr show port1
6: port1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default qlen 1000
    link/ether c0:ff:ee:00:00:11 brd ff:ff:ff:ff:ff:ff
    inet 10.0.0.11/24 brd 10.0.0.255 scope global dynamic port1
       valid_lft 577sec preferred_lft 577sec
    inet6 fe80::c2ff:eeff:fe00:11/64 scope link
       valid_lft forever preferred_lft forever
```

## Configuring port2 on ovn1

Let's repeat the above process with `port2`, again using host `ovn1`. First we add the port:

```
ovs-vsctl add-port br-int port2 -- \
  set interface port2 \
    type=internal \
    mac='["c0:ff:ee:00:00:12"]' \
    external_ids:iface-id=port2
```

Add it to a namespace:

```
ip netns add vm2
ip link set netns vm2 port2
ip -n vm2 addr add 127.0.0.1/8 dev lo
ip -n vm2 link set lo up
```

Configure it using `dhclient`:

```
ip netns exec vm2 dhclient -v -i port2 --no-pid
```


And finally look at the OVN port bindings on `ovn0`:

```
[root@ovn0 ~]# ovn-sbctl show
Chassis ovn1
    hostname: ovn1.virt
    Encap geneve
        ip: "192.168.122.101"
        options: {csum="true"}
    Port_Binding port2
    Port_Binding port1
Chassis ovn0
    hostname: ovn0.virt
    Encap geneve
        ip: "192.168.122.100"
        options: {csum="true"}
Chassis ovn2
    hostname: ovn2.virt
    Encap geneve
        ip: "192.168.122.102"
        options: {csum="true"}
```

## Configuring port3 on ovn2

Lastly, let's repeat the above process for `port3` on host `ovn2`.

```
ovs-vsctl add-port br-int port3 -- \
  set interface port3 \
    type=internal \
    mac='["c0:ff:ee:00:00:13"]' \
    external_ids:iface-id=port3
ip netns add vm3
ip link set netns vm3 port3
ip -n vm3 addr add 127.0.0.1/8 dev lo
ip -n vm3 link set lo up
ip netns exec vm3 dhclient -v -i port3 --no-pid
```

When we're done, `ovn-sbctl show` looks like:

```
[root@ovn0 ~]# ovn-sbctl show
Chassis ovn1
    hostname: ovn1.virt
    Encap geneve
        ip: "192.168.122.101"
        options: {csum="true"}
    Port_Binding port2
    Port_Binding port1
Chassis ovn0
    hostname: ovn0.virt
    Encap geneve
        ip: "192.168.122.100"
        options: {csum="true"}
Chassis ovn2
    hostname: ovn2.virt
    Encap geneve
        ip: "192.168.122.102"
        options: {csum="true"}
    Port_Binding port3
```

## Verify connectivity

We can verify that the network namespaces we've created in the above examples are able to communicate with each other regardless of the host on which they have been created.  For example, if we log into `ovn2` we can show that we are able to reach the address of `port1` (`10.0.0.11`) from `port3`:

```
[root@ovn2 ~]# ip netns exec vm3 ping -c1 10.0.0.11
PING 10.0.0.11 (10.0.0.11) 56(84) bytes of data.
64 bytes from 10.0.0.11: icmp_seq=1 ttl=64 time=0.266 ms

--- 10.0.0.11 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.266/0.266/0.266/0.000 ms
```

# That's all folks!

I hope this post helps you understand how to set up a simple OVN environment with DHCP. Please feel free to leave comments and questions!

## Thanks to

- [Lorenzo Bianconi](https://github.com/LorenzoBianconi) for helping sort this out over email.
- [Han Zhou](https://twitter.com/zhouhanok) for helping solve the issue around Geneve tunnels coming up appropriately.

## See also

Below are some of the resources to which I referred while figuring out how to put this all together:

- [Dynamic IP address management in Open Virtual Network (OVN): Part One](https://developers.redhat.com/blog/2018/09/03/ovn-dynamic-ip-address-management/)
- [Dynamic IP address management in Open Virtual Network (OVN): Part Two](https://developers.redhat.com/blog/2018/09/27/dynamic-ip-address-management-in-open-virtual-network-ovn-part-two/)
- [Run Open Virtual Network (OVN) in Ubuntu](https://qyx.me/2018/07/10/run-and-test-ovn/)
- [Simple OVN setup in 5 minutes](http://dani.foroselectronica.es/simple-ovn-setup-in-5-minutes-491/)
