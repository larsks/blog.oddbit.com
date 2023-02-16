---
categories: [tech]
aliases: ["/2014/05/28/booting-an-instance-with-multi/"]
title: Booting an instance with multiple fixed addresses
date: "2014-05-28"
tags:
- openstack
- neutron
- networking
---

This article expands on my answer to [Add multiple specific IPs to
instance][1], a question posted to [ask.openstack.org][].

[1]: https://ask.openstack.org/en/question/30690/add-multiple-specific-ips-to-instance/
[ask.openstack.org]: https://ask.openstack.org/

In order to serve out SSL services from an OpenStack instance, you
will generally want one local ip address for each SSL virtual host you
support.  It is possible to create an instance with multiple fixed
addresses, but there are a few complications to watch out for.

Assumptions
===========

This article assumes that the following resources exist:

- a private network `net0`.
- a private network `net0-subnet0`, associated with `net0`, assigned
  the range `10.0.0.0/24`.
- a public network `external` assigned the range `192.168.200.0/24`.
- an image named `fedora-20-x86_64`, with hopefully self-evident
  contents.

Creating a port
===============

Start by creating a port in Neutron:

    $ neutron port-create net0 \
      --fixed-ip subnet_id=net0-subnet0 \
      --fixed-ip subnet_id=net0-subnet0

This will create a neutron port to which have been allocated to fixed
ip addresses from `net0-subnet0`:

    +-----------------------+----------------------------------------------------------------------------------+
    | Field                 | Value                                                                            |
    +-----------------------+----------------------------------------------------------------------------------+
    | admin_state_up        | True                                                                             |
    | allowed_address_pairs |                                                                                  |
    | binding:vnic_type     | normal                                                                           |
    | device_id             |                                                                                  |
    | device_owner          |                                                                                  |
    | fixed_ips             | {"subnet_id": "f8ca90fd-cb82-4218-9627-6fa66e4c9c3c", "ip_address": "10.0.0.18"} |
    |                       | {"subnet_id": "f8ca90fd-cb82-4218-9627-6fa66e4c9c3c", "ip_address": "10.0.0.19"} |
    | id                    | 3c564dd5-fd45-4f61-88df-715f71667b3b                                             |
    | mac_address           | fa:16:3e:e1:15:7f                                                                |
    | name                  |                                                                                  |
    | network_id            | bb4e5e37-74e1-41bd-880e-b59e94236c5e                                             |
    | security_groups       | 52f7a87c-380f-4a07-a6ff-d64be495f25b                                             |
    | status                | DOWN                                                                             |
    | tenant_id             | 4dfe8e38f68449b6a0c9cd73037726f7                                                 |
    +-----------------------+----------------------------------------------------------------------------------+

If you want, you can specify an explicit set of addresses rather than
having neutron allocate them for you:

    $ neutron port-create net0 \
      --fixed-ip subnet_id=net0-subnet0,ip_address=10.0.0.18 \
      --fixed-ip subnet_id=net0-subnet0,ip_address=10.0.0.19

Boot an instance
================

You can boot an instance using this port using the `port-id=...`
parameter to the `--nic` option:

    $ nova boot \
      --nic port-id=3c564dd5-fd45-4f61-88df-715f71667b3b \
      --flavor m1.tiny \
      --image fedora-20-x86_64 \
      --key-name lars test0

This is where the first complication arises: the instance will boot
and receive a DHCP lease for one of the fixed addresses you created,
but you don't know which one.  This isn't an insurmountable problem;
you can assign floating ips to each one and then try logging in to
both and see which works.

Rather than playing network roulette, you can pass in a script via the
`--user-data` option that will take care of configuring the network
correctly.  For example, something like this:

    #!/bin/sh

    cat > /etc/sysconfig/network-scripts/ifcfg-eth0 <<EOF
    DEVICE=eth0
    BOOTPROTO=none
    IPADDR=10.0.0.18
    NETMASK=255.255.255.0
    GATEWAY=10.0.0.1
    ONBOOT=yes
    EOF

    cat > /etc/sysconfig/network-scripts/ifcfg-eth0:0 <<EOF
    DEVICE=eth0:0
    BOOTPROTO=none
    IPADDR=10.0.0.19
    NETMASK=255.255.255.0
    GATEWAY=10.0.0.1
    ONBOOT=yes
    EOF

    ifdown eth0
    ifup eth0
    ifup eth0:0

And boot the instance like this:

    $ nova boot --nic port-id=3c564dd5-fd45-4f61-88df-715f71667b3b \
      --flavor m1.tiny --image fedora-20-x86_64 --key-name lars \
      --user-data userdata.txt test0

Assuming that your image uses [cloud-init][] or something similar, it
should execute the `user-data` script at boot and set up the
persistent network configuration.

[cloud-init]: http://cloudinit.readthedocs.org/en/latest/

At this stage, you can verify that both addresses have been assigned
by using the `ip netns` command to run `ping` inside an appropriate
namespace.  Something like:

    $ sudo ip netns exec qdhcp-bb4e5e37-74e1-41bd-880e-b59e94236c5e ping -c1 10.0.0.18
    PING 10.0.0.18 (10.0.0.18) 56(84) bytes of data.
    64 bytes from 10.0.0.18: icmp_seq=1 ttl=64 time=1.60 ms

    --- 10.0.0.18 ping statistics ---
    1 packets transmitted, 1 received, 0% packet loss, time 0ms
    rtt min/avg/max/mdev = 1.606/1.606/1.606/0.000 ms

    $ sudo ip netns exec qdhcp-bb4e5e37-74e1-41bd-880e-b59e94236c5e ping -c1 10.0.0.19
    PING 10.0.0.19 (10.0.0.19) 56(84) bytes of data.
    64 bytes from 10.0.0.19: icmp_seq=1 ttl=64 time=1.60 ms

    --- 10.0.0.19 ping statistics ---
    1 packets transmitted, 1 received, 0% packet loss, time 0ms
    rtt min/avg/max/mdev = 1.701/1.701/1.701/0.000 ms

This assumes that the UUID of the `net0` network is `bb4e5e37-74e1-41bd-880e-b59e94236c5e`.  On your system, the namespace will be something different.

Assign floating ips
===================

Assign a floating ip address to each of the fixed addresses.  You will
need to use the `--fixed-address` option to `nova add-floating-ip`:

    $ nova add-floating-ip --fixed-address 10.0.0.19 test0 192.168.200.6
    $ nova add-floating-ip --fixed-address 10.0.0.18 test0 192.168.200.4

With these changes in place, the system is accessible via either
address:

    $ ssh fedora@192.168.200.4 uptime
      14:51:52 up 4 min,  0 users,  load average: 0.00, 0.02, 0.02
    $ ssh fedora@192.168.200.6 uptime
      14:51:54 up 4 min,  0 users,  load average: 0.00, 0.02, 0.02

And looking at the network configuration on the system, we can see
that both addresses have been assigned to `eth0` as expected:

    $ ssh fedora@192.168.200.4 /sbin/ip a
    [...]
    2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
        link/ether fa:16:3e:bf:f9:6a brd ff:ff:ff:ff:ff:ff
        inet 10.0.0.18/24 brd 10.0.0.255 scope global eth0
           valid_lft forever preferred_lft forever
        inet 10.0.0.19/24 brd 10.0.0.255 scope global secondary eth0:0
           valid_lft forever ...

