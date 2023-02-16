---
categories: [tech]
aliases: ["/2014/08/11/four-ways-to-connect-a-docker/"]
title: Four ways to connect a docker container to a local network
date: "2014-08-11"
tags:
  - networking
  - docker
  - openvswitch
---

**Update (2018-03-22)** Since I wrote this document back in 2014,
Docker has developed the [macvlan network
driver](https://docs.docker.com/network/macvlan/). That gives you a
*supported* mechanism for direct connectivity to a local layer 2
network.  I've [written an article about working with the macvlan
driver](/2018/03/12/using-docker-macvlan-networks/).

---

This article discusses four ways to make a Docker container appear on
a local network.  These are not suggested as practical solutions, but
are meant to illustrate some of the underlying network technology
available in Linux.

If you were actually going to use one of these solutions as anything
other than a technology demonstration, you might look to the [pipework][] script, which can automate many of these configurations.

[pipework]: https://github.com/jpetazzo/pipework

## Goals and Assumptions

In the following examples, we have a host with address 10.12.0.76 on
the 10.12.0.0/21 network.  We are creating a Docker container that we
want to expose as 10.12.0.117.

I am running Fedora 20 with Docker 1.1.2.  This means, in particular,
that my `utils-linux` package is recent enough to include the
[nsenter][] command. If you don't have that handy, there is a
convenient Docker recipe to build it for you at [jpetazzo/nsenter][]
on GitHub.

[jpetazzo/nsenter]: https://github.com/jpetazzo/nsenter

## A little help along the way

In this article we will often refer to the PID of a docker container.
In order to make this convenient, drop the following into a script
called `docker-pid`, place it somewhere on your `PATH`, and make it
executable:

    #!/bin/sh

    exec docker inspect --format '{{ .State.Pid }}' "$@"

This allows us to conveniently get the PID of a docker container by
name or ID:

    $ docker-pid web
    22041

In a script called `docker-ip`, place the following:

    #!/bin/sh

    exec docker inspect --format '{{ .NetworkSettings.IPAddress }}' "$@"

And now we can get the ip address of a container like this:

    $ docker-ip web
    172.17.0.4

## Using NAT

This uses the standard Docker network model combined with NAT rules on
your host to redirect inbound traffic to/outbound traffic from the
appropriate IP address.

Assign our target address to your host interface:

    # ip addr add 10.12.0.117/21 dev em1

Start your docker container, using the `-p` option to bind exposed
ports to an ip address and port on the host:

    # docker run -d --name web -p 10.12.0.117:80:80 larsks/simpleweb

With this command, Docker will set up the [standard network][] model:

- It will create a [veth][] interface pair.
- Connect one end to the `docker0` bridge.
- Place the other inside the container namespace as `eth0`.
- Assign an ip address from the network used by the `docker0` bridge.

[veth]: http://lwn.net/Articles/232688/
[standard network]: https://docs.docker.com/articles/networking/

Because we added `-p 10.12.0.117:80:80` to our command line, Docker
will also create the following rule in the `nat` table `DOCKER`
chain (which is run from the `PREROUTING` chain):

    -A DOCKER -d 10.12.0.117/32 ! -i docker0 -p tcp -m tcp 
      --dport 80 -j DNAT --to-destination 172.17.0.4:80

This matches traffic TO our target address (`-d 10.12.0.117/32`) not
originating on the `docker0` bridge (`! -i docker0`) destined for
`tcp` port `80` (`-p tcp -m tcp --dport 80`).  Matching traffic has
it's destination set to the address of our docker container (`-j DNAT --to-destination 172.17.0.4:80`).

From a host elsewhere on the network, we can now access the web server
at our selected ip address:

    $ curl http://10.12.0.117/hello.html
    Hello world

If our container were to initiate a network connection with another
system, that connection would appear to originate with ip address of
our *host*.  We can fix that my adding a `SNAT` rule to the
`POSTROUTING` chain to modify the source address:

    # iptables -t nat -I POSTROUTING -s $(docker-ip web) \
        -j SNAT --to-source 10.12.0.117

Note here the use of `-I POSTROUTING`, which places the rule at the
*top* of the `POSTROUTING` chain.  This is necessary because, by
default, Docker has already added the following rule to the top of the
`POSTROUTING` chain:

    -A POSTROUTING -s 172.17.0.0/16 ! -d 172.17.0.0/16 -j MASQUERADE

Because this `MASQUERADE` rule matches traffic from any container, we
need to place our rule earlier in the `POSTROUTING` chain for it to
have any affect.

With these rules in place, traffic to 10.12.0.117 (port 80) is
directed to our `web` container, and traffic *originating* in the web
container will appear to come from 10.12.0.117.

## With Linux Bridge devices

The previous example was relatively easy to configure, but has a few
shortcomings.  If you need to configure an interface using DHCP, or if
you have an application that needs to be on the same layer 2 broadcast
domain as other devices on your network, NAT rules aren't going to
work out.

This solution uses a Linux bridge device, created using `brctl`, to
connect your containers directly to a physical network.

Start by creating a new bridge device.  In this example, we'll create
one called `br-em1`:

    # brctl addbr br-em1
    # ip link set br-em1 up

We're going to add `em1` to this bridge, and move the ip address from
`em1` onto the bridge.

**WARNING**: This is not something you should do remotely, especially
for the first time, and making this persistent varies from
distribution to distribution, so this will not be a persistent
configuration.

Look at the configuration of interface `em1` and note the existing ip
address:

    # ip addr show em1
    2: em1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq master br-em1 state UP group default qlen 1000
        link/ether 00:1d:09:63:71:30 brd ff:ff:ff:ff:ff:ff
        inet 10.12.0.76/21 scope global br-em1
           valid_lft forever preferred_lft forever

Look at your current routes and note the default route:

    # ip route
    default via 10.12.7.254 dev em1 
    10.12.0.0/21 dev em1  proto kernel  scope link  src 10.12.0.76 

Now, add this device to your bridge:

    # brctl addif br-em1 em1

Configure the bridge with the address that used to belong to
`em1`:

    # ip addr del 10.12.0.76/21 dev em1
    # ip addr add 10.12.0.76/21 dev br-em1

And move the default route to the bridge:

    # ip route del default
    # ip route add default via 10.12.7.254 dev br-em1

If you were doing this remotely; you would do this all in one line
like this:

    # ip addr add 10.12.0.76/21 dev br-em1; \
        ip addr del 10.12.0.76/21 dev em1; \
        brctl addif br-em1 em1; \
        ip route del default; \
        ip route add default via 10.12.7.254 dev br-em1

At this point, verify that you still have network connectivity:

    # curl http://google.com/
    <HTML><HEAD><meta http-equiv="content-type" content="text/html;charset=utf-8">
    [...]

Start up the web container:

    # docker run -d --name web larsks/simpleweb

This will give us the normal `eth0` interface inside the container,
but we're going to ignore that and add a new one.

Create a [veth][] interface pair:

    # ip link add web-int type veth peer name web-ext

Add the `web-ext` link to the `br-eth0` bridge:

    # brctl addif br-em1 web-ext

And add the `web-int` interface to the namespace of the container:

    # ip link set netns $(docker-pid web) dev web-int

Next, we'll use the [nsenter][] command (part of the `util-linux` package) to run some commands inside the `web` container.  Start by bringing up the link inside the container:

[nsenter]: http://man7.org/linux/man-pages/man1/nsenter.1.html

    # nsenter -t $(docker-pid web) -n ip link set web-int up

Assign our target ip address to the interface:

    # nsenter -t $(docker-pid web) -n ip addr add 10.12.0.117/21 dev web-int

And set a new default route inside the container:

    # nsenter -t $(docker-pid web) -n ip route del default
    # nsenter -t $(docker-pid web) -n ip route add default via 10.12.7.254 dev web-int

Again, we can verify from another host that the web server is
available at 10.12.0.117:

    $ curl http://10.12.0.117/hello.html
    Hello world

Note that in this example we have assigned a static ip address, but we
could just have easily acquired an address using DHCP.  After running:

    # nsenter -t $(docker-pid web) -n ip link set web-int up

We can run:

    # nsenter -t $(docker-pid web) -n -- dhclient -d web-int
    Internet Systems Consortium DHCP Client 4.2.6
    Copyright 2004-2014 Internet Systems Consortium.
    All rights reserved.
    For info, please visit https://www.isc.org/software/dhcp/

    Listening on LPF/web-int/6e:f0:a8:c6:f0:43
    Sending on   LPF/web-int/6e:f0:a8:c6:f0:43
    Sending on   Socket/fallback
    DHCPDISCOVER on web-int to 255.255.255.255 port 67 interval 4 (xid=0x3aaab45b)
    DHCPREQUEST on web-int to 255.255.255.255 port 67 (xid=0x3aaab45b)
    DHCPOFFER from 10.12.7.253
    DHCPACK from 10.12.7.253 (xid=0x3aaab45b)
    bound to 10.12.6.151 -- renewal in 714 seconds.

## With Open vSwitch Bridge devices

This process is largely the same as in the previous example, but we
use [Open vSwitch][] instead of the legacy Linux bridge devices.
These instructions assume that you have already installed and started
Open vSwitch on your system.

[open vswitch]: http://openvswitch.org/

Create an OVS bridge using the `ovs-vsctl` command:

    # ovs-vsctl add-br br-em1
    # ip link set br-em1 up

And add your external interface:

    # ovs-vsctl add-port br-em1 em1

And then proceed as in the previous set of instructions.

The equivalent all-in-one command is:

    # ip addr add 10.12.0.76/21 dev br-em1; \
        ip addr del 10.12.0.76/21 dev em1; \
        ovs-vsctl add-port br-em1 em1; \
        ip route del default; \
        ip route add default via 10.12.7.254 dev br-em1

Once that completes, your openvswitch configuration should look like
this:

    # ovs-vsctl show
    0b1d5895-88e6-42e5-a1da-ad464c75198c
        Bridge "br-em1"
            Port "br-em1"
                Interface "br-em1"
                    type: internal
            Port "em1"
                Interface "em1"
        ovs_version: "2.1.2"

To add the `web-ext` interface to the bridge, run:

    # ovs-vsctl add-port br-em1 web-ext

Instead of:

    # brctl addif br-em1 web-ext

**WARNING**: The Open vSwitch configuration persists between reboots.
This means that when your system comes back up, `em1` will still be a
member of `br-em`, which will probably result in no network
connectivity for your host.

Before rebooting your system, make sure to `ovs-vsctl del-port br-em1
em1`.

## With macvlan devices

This process is similar to the previous two, but instead of using a
bridge device we will create a [macvlan][], which is a virtual network
interface associated with a physical interface.  Unlike the previous
two solutions, this does not require any interruption to your primary
network interface.

Start by creating a docker container as in the previous examples:

    # docker run -d --name web larsks/simpleweb

Create a `macvlan` interface associated with your physical interface:

    # ip link add em1p0 link em1 type macvlan mode bridge

This creates a new `macvlan` interface named `em1p0` (but you can
name it anything you want) associated with interface `em1`.  We are
setting it up in `bridge` mode, which permits all `macvlan` interfaces
to communicate with eachother.

Add this interface to the container's network namespace:

    # ip link set netns $(docker-pid web) em1p0

Bring up the link:

    # nsenter -t $(docker-pid web) -n ip link set em1p0 up

And configure the ip address and routing:

    # nsenter -t $(docker-pid web) -n ip route del default
    # nsenter -t $(docker-pid web) -n ip addr add 10.12.0.117/21 dev em1p0
    # nsenter -t $(docker-pid web) -n ip route add default via 10.12.7.254 dev em1p0

And demonstrate that *from another host* the web server is available
at 10.12.0.117:

    $ curl http://10.12.0.117/hello.html
    Hello world

But note that if you were to try the same thing on the host, you would
get:

    curl: (7) Failed connect to 10.12.0.117:80; No route to host

The *host* is unable to communicate with `macvlan` devices via the
primary interface.  You can create *another* `macvlan` interface on
the host, give it an address on the appropriate network, and then set
up routes to your containers via that interface:

    # ip link add em1p1 link em1 type macvlan mode bridge
    # ip addr add 10.12.6.144/21 dev em1p1
    # ip route add 10.12.0.117 dev em1p1

[macvlan]: http://backreference.org/2014/03/20/some-notes-on-macvlanmacvtap/

