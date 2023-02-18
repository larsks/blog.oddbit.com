---
categories:
- tech
date: '2023-02-19'
toc: true
tags:
- mininet
- nat
- networking
- routing
- stackexchange
- vrf
title: NAT between identical networks using VRF
---

Last week, Oskar Stenberg asked on [Unix & Linux](https://unix.stackexchange.com/q/735931/4989) if it were possible to configure connectivity between two networks, both using the same address range, without involving network namespaces. That is, given this high level view of the network...

[![two networks with the same address range connected by a host named "middleman"][1]][2]

[1]: the-problem.svg
[2]: https://excalidraw.com/#json=uuXRRZ2ybaAXiUvbQVkNO,krx3lsbf12c-tDhuWtRjbg

...can we set things up so that hosts on the "inner" network can communicate with hosts on the "outer" network using the range `192.168.3.0/24`, and similarly for communication in the other direction?

## Setting up a lab

When investigating this sort of networking question, I find it easiest to reproduce the topology in a virtual environment so that it's easy to test things out. I generally use [Mininet][] for this, which provides a simple Python API for creating virtual nodes and switches and creating links between them.

[mininet]: https://mininet.org

I created the following network topology for this test:

{{< figure src="topology-1.svg" alt="virtual network topology diagram" position="center" >}}

In the rest of this post, I'll be referring to these hostnames.

See the bottom of this post for a link to the repository that contains the complete test environment.

## VRF in theory

VRF stands for "Virtual Routing and Forwarding". From the [Wikipedia article on the topic][]:

> In IP-based computer networks, virtual routing and forwarding (VRF) is a technology that allows multiple instances of a routing table to co-exist within the same router at the same time. One or more logical or physical interfaces may have a VRF and these VRFs do not share routes therefore the packets are only forwarded between interfaces on the same VRF. VRFs are the TCP/IP layer 3 equivalent of a VLAN. Because the routing instances are independent, the same or overlapping IP addresses can be used without conflicting with each other. Network functionality is improved because network paths can be segmented without requiring multiple routers.[1]

[wikipedia article on the topic]: https://en.wikipedia.org/wiki/Virtual_routing_and_forwarding

In Linux, VRF support is implemented as a [special type of network device][vrf-dev]. A VRF device sets up an isolated routing domain; network traffic on devices associated with a VRF will use the routing table associated with that VRF, rather than the main routing table, which permits us to connect multiple networks with overlapping address ranges.

We can create new VRF devices with the `ip link add` command:

```
ip link add vrf-inner type vrf table 100
```

Running the above command results in the following changes:

- It creates a new network device named `vrf-inner`
- It adds a new route policy rule (if it doesn't already exist) that looks like:

  ```
  1000:   from all lookup [l3mdev-table]
  ```

  This causes route lookups to use the appropriate route table for interfaces associated with a VRF.

After creating a VRF device, we can add interfaces to it like this:

```
ip link set eth0 master vrf-inner
```

This associates the given interface with the VRF device, and it moves all routes associated with the interface out of the `local` and `main` routing tables and into the VRF-specific routing table.

[vrf-dev]: https://docs.kernel.org/networking/vrf.html

You can see a list of vrf devices by running `ip vrf show`:

```
# ip vrf show
Name              Table
-----------------------
vrf-inner          100
```

You can see a list of devices associated with a particular VRF with the `ip link` command:

```
# ip -brief link show master vrf-inner
eth0@if448 UP             72:87:af:d3:b5:f9 <BROADCAST,MULTICAST,UP,LOWER_UP>
```

## VRF in practice

We're going to create two VRF devices on the `middleman` host; one associated with the "inner" network and one associated with the "outer" network. In our virtual network topology, the `middleman` host has two network interfaces:

- `middleman-eth0` is connected to the "inner" network
- `middleman-eth1` is connected to the "outer" network

Both devices have the same address (`192.168.2.1`):

```
# ip addr show
2: middleman-eth0@if426: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master vrf-inner state UP group default qlen 1000
    link/ether 32:9e:01:2e:78:2f brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 192.168.2.1/24 brd 192.168.2.255 scope global middleman-eth0
       valid_lft forever preferred_lft forever
root@mininet-vm:~/unix-735931# ip addr show middleman-eth1
3: middleman-eth1@if427: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master vrf-outer state UP group default qlen 1000
    link/ether 12:be:9a:09:33:93 brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 192.168.2.1/24 brd 192.168.2.255 scope global middleman-eth1
       valid_lft forever preferred_lft forever
```

And the main routing table looks like this:

```
# ip route show
192.168.2.0/24 dev middleman-eth1 proto kernel scope link src 192.168.2.1 
192.168.2.0/24 dev middleman-eth0 proto kernel scope link src 192.168.2.1 
```

If you're at all familiar with Linux network configuration, that probably looks weird. Right now this isn't a particularly functional network configuration, but we can fix that!

To create our two VRF devices, we run the following commands:

```
ip link add vrf-inner type vrf table 100
ip link add vrf-outer type vrf table 200
ip link set vrf-inner up
ip link set vrf-outer up
```

This associates `vrf-inner` with route table 100, and `vrf-outer` with route table 200. At this point, tables 100 and 200 are empty:

```
# ip route show table 100
Error: ipv4: FIB table does not exist.
Dump terminated
# ip route show table 200
Error: ipv4: FIB table does not exist.
Dump terminated
```

Next, we add our interfaces to the appropriate VRF devices:

```
ip link set middleman-eth0 master vrf-inner
ip link set middleman-eth1 master vrf-outer
```

After running these commands, there are no routes left in the main routing table:

```
# ip route show
<no output>
```

And the routes associated with our two physical interfaces are now contained by the appropriate VRF routing tables. Here's table 100:

```
root@mininet-vm:~/unix-735931# ip route show table 100
broadcast 192.168.2.0 dev middleman-eth0 proto kernel scope link src 192.168.2.1 
192.168.2.0/24 dev middleman-eth0 proto kernel scope link src 192.168.2.1 
local 192.168.2.1 dev middleman-eth0 proto kernel scope host src 192.168.2.1 
broadcast 192.168.2.255 dev middleman-eth0 proto kernel scope link src 192.168.2.1 
```

And table 200:

```
root@mininet-vm:~/unix-735931# ip route show table 200
broadcast 192.168.2.0 dev middleman-eth1 proto kernel scope link src 192.168.2.1 
192.168.2.0/24 dev middleman-eth1 proto kernel scope link src 192.168.2.1 
local 192.168.2.1 dev middleman-eth1 proto kernel scope host src 192.168.2.1 
broadcast 192.168.2.255 dev middleman-eth1 proto kernel scope link src 192.168.2.1 
```

This configuration effectively gives us two isolated networks:

{{< figure src="topology-2.svg" alt="virtual network topology diagram" position="center" >}}

We can verify that nodes in the "inner" and "outer" networks are now able to communicate with `middleman`. We can reach `middleman` from `innernode0`; in this case, we're communicating with interface `middleman-eth0`:

```
innernode0# ping -c1 192.168.2.1
PING 192.168.2.1 (192.168.2.1) 56(84) bytes of data.
64 bytes from 192.168.2.1: icmp_seq=1 ttl=64 time=0.126 ms

--- 192.168.2.1 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.126/0.126/0.126/0.000 ms
```

Similarly, we can reach `middleman` from `outernode`, but in this case we're communicating with interface `middleman-eth1`:

```
outernode0# ping -c1 192.168.2.1
PING 192.168.2.1 (192.168.2.1) 56(84) bytes of data.
64 bytes from 192.168.2.1: icmp_seq=1 ttl=64 time=1.02 ms

--- 192.168.2.1 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 1.020/1.020/1.020/0.000 ms
```

## Configure routing on the nodes

Our goal is to let nodes on one side of the network to use the address range `192.168.3.0/24` to refer to nodes on the other side of the network. Right now, if we were to try to access `192.168.3.10` from `innernode0`, the  attempt would fail with:

```
innernode0# ping 192.168.3.10
ping: connect: Network is unreachable
```

The "network is unreachable" message means that `innernode0` has no idea where to send that request. That's because at the moment, the routing table on all the nodes look like:

```
innernode0# ip route
192.168.2.0/24 dev outernode0-eth0 proto kernel scope link src 192.168.2.10 
```

There is neither a default gateway nor a network-specific route appropriate for `192.168.3.0/24` addresses. Let's add a network route that will route that address range through `middleman`:

```
innernode0# ip route add 192.168.3.0/24 via 192.168.2.1
innernode0# ip route
192.168.2.0/24 dev innernode0-eth0 proto kernel scope link src 192.168.2.10 
192.168.3.0/24 via 192.168.2.1 dev innernode0-eth0 
```

This same change needs to be made on all the `innernode*` and `outernode*` nodes.

With the route in place, attempts to reach `192.168.3.10` from `innernode0` will still fail, but now they're getting rejected by `middleman` because *it* doesn't have any appropriate routes:

```
innernode0# ping -c1 192.168.3.10
PING 192.168.3.10 (192.168.3.10) 56(84) bytes of data.
From 192.168.2.1 icmp_seq=1 Destination Net Unreachable

--- 192.168.3.10 ping statistics ---
1 packets transmitted, 0 received, +1 errors, 100% packet loss, time 0ms
```

We need to tell `middleman` what to do with these packets.

## Configure routing and NAT on middleman

In order to achieve our desired connectivity, we need to:

1. Map the `192.168.3.0/24` destination address to the equivalent `192.168.2.0/24` address *before* the kernel makes a routing decision.
2. Map the `192.168.2.0/24` source address to the equivalent `192.168.3.0/24` address *after* the kernel makes a routing decision (so that replies will go back to "other" side).
3. Ensure that the kernel uses the routing table for the *target* network when making routing decisions for these connections.

We can achieve (1) and (2) using the netfilter [`NETMAP`][netmap] extension by adding the following two rules:

```
iptables -t nat -A PREROUTING -d 192.168.3.0/24 -j NETMAP --to 192.168.2.0/24
iptables -t nat -A POSTROUTING -s 192.168.2.0/24 -j NETMAP --to 192.168.3.0/24
```

For incoming traffic destined for the 192.168.3.0/24 network, this maps the destination address to the matching `192.168.2.0/24` address. For outgoing traffic with a source address on the `192.168.2.0/24` network, this maps the source to the equivalent `192.168.3.0/24` network (so that the recipient see the traffic as coming from "the other side").

(For those of you wondering, "can we do this using `nftables` instead?", as of this writing [`nftables` does not appear to have `NETMAP` support][nft-netmap], so we have to use `iptables` for this step.)

[netmap]: https://www.netfilter.org/documentation/HOWTO/netfilter-extensions-HOWTO-4.html#ss4.4
[nft-netmap]: https://wiki.nftables.org/wiki-nftables/index.php/Supported_features_compared_to_xtables#NETMAP

With this change in place, re-trying that `ping` command on `innernode0` will apparently succeed:

```
innernode0 ping -c1 192.168.3.10
PING 192.168.3.10 (192.168.3.10) 56(84) bytes of data.
64 bytes from 192.168.3.10: icmp_seq=1 ttl=63 time=0.063 ms

--- 192.168.3.10 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.063/0.063/0.063/0.000 ms
```

However, running `tcpdump` on `middleman` will show us that we haven't yet achieved our goal:

```
12:59:52.899054 middleman-eth0 In  IP 192.168.2.10 > 192.168.3.10: ICMP echo request, id 16520, seq 1, length 64
12:59:52.899077 middleman-eth0 Out IP 192.168.3.10 > 192.168.2.10: ICMP echo request, id 16520, seq 1, length 64
12:59:52.899127 middleman-eth0 In  IP 192.168.2.10 > 192.168.3.10: ICMP echo reply, id 16520, seq 1, length 64
12:59:52.899130 middleman-eth0 Out IP 192.168.3.10 > 192.168.2.10: ICMP echo reply, id 16520, seq 1, length 64
```

You can see that our packet is coming on on `middleman-eth0`...and going right back out the same interface. We have thus far achieved a very complicated loopback interface.

The missing piece is some logic to have the kernel use the routing table for the "other side" when making routing decisions for these packets. We're going to do that by:

1. Tagging packets with a mark that indicates the interface on which they were recieved
2. Using this mark to select an appropriate routing table

We add the packet mark by adding these rules to the `MANGLE` table `PREROUTING` chain:

```
iptables -t mangle -A PREROUTING -i middleman-eth0 -d 192.168.3.0/24 -j MARK --set-mark 100
iptables -t mangle -A PREROUTING -i middleman-eth1 -d 192.168.3.0/24 -j MARK --set-mark 200
```

And we utilize that mark in route lookups by adding the following two route policy rules:

```
ip rule add prio 100 fwmark 100 lookup 200
ip rule add prio 200 fwmark 200 lookup 100
```

It is critical that these rules come before (aka "have a higher priority than", aka "have a lower number than") the `l3mdev` rule added when we created the VRF devices.

## Validation: Does it actually work?

With that last set of changes in place, if we repeat the `ping` test from `innernode0` to `outernode0` and run `tcpdump` on `middleman`, we see:

```
13:05:27.667793 middleman-eth0 In  IP 192.168.2.10 > 192.168.3.10: ICMP echo request, id 16556, seq 1, length 64
13:05:27.667816 middleman-eth1 Out IP 192.168.3.10 > 192.168.2.10: ICMP echo request, id 16556, seq 1, length 64
13:05:27.667863 middleman-eth1 In  IP 192.168.2.10 > 192.168.3.10: ICMP echo reply, id 16556, seq 1, length 64
13:05:27.667868 middleman-eth0 Out IP 192.168.3.10 > 192.168.2.10: ICMP echo reply, id 16556, seq 1, length 64
```

Now we finally see the desired behavior: the request from `innernode0` comes in on `eth0`, goes out on `eth1` with the addresses appropriately mapped and gets delivered to `outernode0`. The reply from `outernode0` goes through the process in reverse, and arrives back at `innernode0`.

## Connection tracking (or, "One more thing...")

There is a subtle problem with the configuration we've implemented so far: the Linux connection tracking mechanism ("[conntrack][]") by default identifies a connection by the 4-tuple `(source_address, source_port, destination_address, destination_port)`. To understand why this is a problem, assume that we're running a web server on port 80 on all the "inner" and "outer" nodes.

[conntrack]: https://arthurchiao.art/blog/conntrack-design-and-implementation/

To connect from `innernode0` to `outernode0`, we could use the following command. We're using the `--local-port` option here because we want to control the source port of our connections:

```
innernode0# curl --local-port 4000 192.168.3.10
```

To connect from `outernode0` to `innernode0`, we would use the same command:

```
outernode0# curl --local-port 4000 192.168.3.10
```

If we look at the connection tracking table on `middleman`, we will see a single connection:

```
middleman# conntrack -L
tcp      6 115 TIME_WAIT src=192.168.2.10 dst=192.168.3.10 sport=4000 dport=80 src=192.168.2.10 dst=192.168.3.10 sport=80 dport=4000 [ASSURED] mark=0 use=1
```

This happens because the 4-tuple for our two connections is identical. Conflating connections like this can cause traffic to stop flowing if both connections are active at the same time.

We need to provide the connection track subsystem with some additional information to uniquely identify these connections. We can do this by using the netfilter `CT` module to assign each connection to a unique conntrack origination "zone":

```
iptables -t raw -A PREROUTING -s 192.168.2.0/24 -i middleman-eth0 -j CT --zone-orig 100
iptables -t raw -A PREROUTING -s 192.168.2.0/24 -i middleman-eth1 -j CT --zone-orig 200
```

What is a "zone"? From [the patch adding this feature][ctzone]:

> A zone is simply a numerical identifier associated with a network
device that is incorporated into the various hashes and used to
distinguish entries in addition to the connection tuples.

[ctzone]: https://lore.kernel.org/all/4B9158F5.5040205@parallels.com/T/

With these rules in place, if we repeat the test with `curl` we will see two distinct connections:

```
middleman# conntrack -L
tcp      6 117 TIME_WAIT src=192.168.2.10 dst=192.168.3.10 sport=4000 dport=80 zone-orig=100 src=192.168.2.10 dst=192.168.3.10 sport=80 dport=26148 [ASSURED] mark=0 use=1
tcp      6 115 TIME_WAIT src=192.168.2.10 dst=192.168.3.10 sport=4000 dport=80 zone-orig=200 src=192.168.2.10 dst=192.168.3.10 sport=80 dport=4000 [ASSURED] mark=0 use=1
```


## Repository and demo

You can find a complete test environment in [this repository][]; that includes the mininet topology I mentioned at the beginning of this post as well as shell scripts to implement all the address, route, and netfilter configurations.

[this repository]: https://github.com/larsks/unix-example-735931-1-1-nat

And here's a video that runs through the steps described in this post:

{{< youtube "Kws98JNKcxE" >}}
