---
categories: [tech]
aliases: ["/2018/03/12/using-docker-macvlan-networks/"]
title: Using Docker macvlan networks
date: "2018-03-12"
tags:
- networking
- docker
---

A question that crops up regularly on [#docker][] is "How do I attach
a container directly to my local network?" One possible answer to that
question is the [macvlan][] network type, which lets you create
"clones" of a physical interface on your host and use that to attach
containers directly to your local network. For the most part it works
great, but it does come with some minor caveats and limitations. I
would like to explore those here.

[#docker]: https://docs.docker.com/opensource/ways/#docker-users
[macvlan]: https://docs.docker.com/network/macvlan/

For the purpose of this example, let's say we have a host interface
`eno1` that looks like this:

    2: eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
        link/ether 64:00:6a:7d:06:1a brd ff:ff:ff:ff:ff:ff
        inet 192.168.1.24/24 brd 192.168.1.255 scope global dynamic eno1
           valid_lft 73303sec preferred_lft 73303sec
        inet6 fe80::b2c9:3793:303:2a55/64 scope link 
           valid_lft forever preferred_lft forever

To create a macvlan network named `mynet` attached to that interface,
you might run something like this:

    docker network create -d macvlan -o parent=eno1 \
      --subnet 192.168.1.0/24 \
      --gateway 192.168.1.1 \
      mynet

...but don't do that.

## Address assignment

When you create a container attached to your macvlan network, Docker
will select an address from the subnet range and assign it to your
container.  This leads to the potential for conflicts: if Docker picks
an address that has already been assigned to another host on your
network, you have a problem!

You can avoid this by reserving a portion of the subnet range for use
by Docker.  There are two parts to this solution:

- You must configure any DHCP service on your network such that it
  will not assign addresses in a given range.

- You must tell Docker about that reserved range of addresses.

How you accomplish the former depends entirely on your local network
infrastructure and is beyond the scope of this document.  The latter
task is accomplished with the `--ip-range` option to `docker network
create`.

On my local network, my DHCP server will not assign any addresses
above `192.168.1.190`.  I have decided to assign to Docker the subset
`192.168.1.192/27`, which is a range of 32 address starting at
192.168.1.192 and ending at 192.168.1.223.  The corresponding `docker
network create` command would be:

    docker network create -d macvlan -o parent=eno1 \
      --subnet 192.168.1.0/24 \
      --gateway 192.168.1.1 \
      --ip-range 192.168.1.192/27 \
      mynet

Now it is possible to create containers attached to my local network
without worrying about the possibility of ip address conflicts.

## Host access

With a container attached to a macvlan network, you will find that
while it can contact other systems on your local network without a
problem, the container will not be able to connect to your host (and
your host will not be able to connect to your container). This is a
limitation of macvlan interfaces: without special support from a
network switch, your host is unable to send packets to its own macvlan
interfaces.

Fortunately, there is a workaround for this problem: you can create
another macvlan interface on your host, and use that to communicate
with containers on the macvlan network.

First, I'm going to reserve an address from our network range for use
by the host interface by using the `--aux-address` option to `docker
network create`. That makes our final command line look like:

    docker network create -d macvlan -o parent=eno1 \
      --subnet 192.168.1.0/24 \
      --gateway 192.168.1.1 \
      --ip-range 192.168.1.192/27 \
      --aux-address 'host=192.168.1.223' \
      mynet

This will prevent Docker from assigning that address to a container.

Next, we create a new macvlan interface on the host. You can call it
whatever you want, but I'm calling this one `mynet-shim`:

    ip link add mynet-shim link eno1 type macvlan  mode bridge

Now we need to configure the interface with the address we reserved
and bring it up:

    ip addr add 192.168.1.223/32 dev mynet-shim
    ip link set mynet-shim up

The last thing we need to do is to tell our host to use that interface
when communicating with the containers.  This is relatively easy
because we have restricted our containers to a particular CIDR subset
of the local network; we just add a route to that range like this:

    ip route add 192.168.1.192/27 dev mynet-shim

With that route in place, your host will automatically use ths
`mynet-shim` interface when communicating with containers on the
`mynet` network.

Note that the interface and routing configuration presented here is
not persistent -- you will lose if if you were to reboot your host.
How to make it persistent is distribution dependent.
