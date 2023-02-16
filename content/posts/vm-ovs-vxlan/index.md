---
categories: [tech]
title: "Creating a VXLAN overlay network with Open vSwitch"
date: "2021-04-17"
tags:
  - virtualization
  - networking
  - openvswitch
  - vxlan
---

In this post, we'll walk through the process of getting virtual
machines on two different hosts to communicate over an overlay network
created using the support for VXLAN in [Open vSwitch][] (or OVS).

[open vswitch]: https://www.openvswitch.org/

## The test environment

For this post, I'll be working with two systems:

- `node0.ovs.virt` at address 192.168.122.107
- `node1.ovs.virt` at address 192.168.122.174

These hosts are running CentOS 8, although once we get past the
package installs the instructions will be similar for other
distributions.

While reading through this post, remember that unless otherwise
specified we're going to be running the indicated commands on *both*
hosts.

## Install packages

Before we can get started configuring things we'll need to install OVS
and [libvirt][]. While `libvirt` is included with the base CentOS
distribution, for OVS we'll need to add both the [EPEL][] repository
as well as a recent CentOS [OpenStack][] repository (OVS is included
in the CentOS OpenStack repositories because it is required by
OpenStack's networking service):

[libvirt]: https://libvirt.org/
[epel]: https://fedoraproject.org/wiki/EPEL
[openstack]: https://www.openstack.org/

```
yum -y install epel-release centos-release-openstack-victoria
```

With these additional repositories enabled we can now install the
required packages:

```
yum -y install \
  libguestfs-tools-c \
  libvirt \
  libvirt-daemon-kvm \
  openvswitch2.15 \
  tcpdump \
  virt-install
```

## Enable services

We need to start both the `libvirtd` and `openvswitch` services:

```
systemctl enable --now openvswitch libvirtd
```

This command will (a) mark the services to start automatically when
the system boots and (b) immediately start the service.

## Configure libvirt

When `libvirt` is first installed it doesn't have any configured
storage pools. Let's create one in the default location,
`/var/lib/libvirt/images`:

```
virsh pool-define-as default --type dir --target /var/lib/libvirt/images
```

We need to mark the pool active, and we might as well configure it to
activate automatically next time the system boots:

```
virsh pool-start default
virsh pool-autostart default
```

## Configure Open vSwitch

### Create the bridge

With all the prerequisites out of the way we can finally start working
with Open vSwitch. Our first task is to create the OVS bridge that
will host our VXLAN tunnels. To create a bridge named `br0`, we run:

```
ovs-vsctl add-br br0
```

We can inspect the OVS configuration by running `ovs-vsctl show`,
which should output something like:

```
cc1e7217-e393-4e21-97c1-92324d47946d
    Bridge br0
        Port br0
            Interface br0
                type: internal
    ovs_version: "2.15.1"
```

Let's not forget to mark the interface "up":

```
ip link set br0 up
```

### Create the VXLAN tunnels

Up until this point we've been running identical commands on both
`node0` and `node1`. In order to create our VXLAN tunnels, we need to
provide a remote endpoint for the VXLAN connection, which is going to
be "the other host". On `node0`, we run:

```
ovs-vsctl add-port br0 vx_node1 -- set interface vx_node1 \
  type=vxlan options:remote_ip=192.168.122.174
```

This creates a VXLAN interface named `vx_node1` (named that way
because the remote endpoint is `node1`). The OVS configuration now
looks like:

```
cc1e7217-e393-4e21-97c1-92324d47946d
    Bridge br0
        Port vx_node1
            Interface vx_node1
                type: vxlan
                options: {remote_ip="192.168.122.174"}
        Port br0
            Interface br0
                type: internal
    ovs_version: "2.15.1"
```


On `node1` we will run:

```
ovs-vsctl add-port br0 vx_node0 -- set interface vx_node0 \
  type=vxlan options:remote_ip=192.168.122.107
```

Which results in:

```
58451994-e0d1-4bf1-8f91-7253ddf4c016
    Bridge br0
        Port br0
            Interface br0
                type: internal
        Port vx_node0
            Interface vx_node0
                type: vxlan
                options: {remote_ip="192.168.122.107"}
    ovs_version: "2.15.1"
```

At this point, we have a functional overlay network: anything attached
to `br0` on either system will appear to share the same layer 2
network. Let's take advantage of this to connect a pair of virtual
machines.

## Create virtual machines

### Download a base image

We'll need a base image for our virtual machines. I'm going to use the
CentOS 8 Stream image, which we can download to our storage directory
like this:

```
curl -L -o /var/lib/libvirt/images/centos-8-stream.qcow2 \
  https://cloud.centos.org/centos/8-stream/x86_64/images/CentOS-Stream-GenericCloud-8-20210210.0.x86_64.qcow2
```

We need to make sure `libvirt` is aware of the new image:

```
virsh pool-refresh default
```

Lastly, we'll want to set a root password on the image so that we can
log in to our virtual machines:

```
virt-customize -a /var/lib/libvirt/images/centos-8-stream.qcow2 \
  --root-password password:secret
```

### Create the virtual machine

We're going to create a pair of virtual machines (one on each host).
We'll be creating each vm with two network interfaces:

- One will be attached to the libvirt `default` network; this will
  allow us to `ssh` into the vm in order to configure things.
- The second will be attached to the OVS bridge

To create a virtual machine on `node0` named `vm0.0`, run the
following command:

```
virt-install \
  -r 3000 \
  --network network=default \
  --network bridge=br0,virtualport.type=openvswitch \
  --os-variant centos8 \
  --disk pool=default,size=10,backing_store=centos-8-stream.qcow2,backing_format=qcow2 \
  --import \
  --noautoconsole \
  -n vm0.0
```

The most interesting option in the above command line is probably the
one used to create the virtual disk:

```
--disk pool=default,size=10,backing_store=centos-8-stream.qcow2,backing_format=qcow2 \
```

This creates a 10GB "[copy-on-write][]" disk that uses
`centos-8-stream.qcow2` as a backing store. That means that reads will
generally come from the `centos-8-stream.qcow2` image, but writes will
be stored in the new image. This makes it easy for us to quickly
create multiple virtual machines from the same base image.

[copy-on-write]: https://en.wikipedia.org/wiki/Copy-on-write

On `node1` we would run a similar command, although here we're naming
the virtual machine `vm1.0`:

```
virt-install \
  -r 3000 \
  --network network=default \
  --network bridge=br0,virtualport.type=openvswitch \
  --os-variant centos8 \
  --disk pool=default,size=10,backing_store=centos-8-stream.qcow2,backing_format=qcow2 \
  --import \
  --noautoconsole \
  -n vm1.0
```

### Configure networking for vm0.0

On `node0`, get the address of the new virtual machine on the default
network using the `virsh domifaddr` command:

```
[root@node0 ~]# virsh domifaddr vm0.0
 Name       MAC address          Protocol     Address
-------------------------------------------------------------------------------
 vnet2      52:54:00:21:6e:4f    ipv4         192.168.124.83/24
```

Connect to the vm using `ssh`:

```
[root@node0 ~]# ssh 192.168.124.83
root@192.168.124.83's password:
Activate the web console with: systemctl enable --now cockpit.socket

Last login: Sat Apr 17 14:08:17 2021 from 192.168.124.1
[root@localhost ~]#
```

(Recall that the `root` password is `secret`.)

Configure interface `eth1` with an address. For this post, we'll use
the `10.0.0.0/24` range for our overlay network. To assign this vm the
address `10.0.0.10`, we can run:

```
ip addr add 10.0.0.10/24 dev eth1
ip link set eth1 up
```

### Configure networking for vm1.0

We need to repeat the process for `vm1.0` on `node1`:

```
[root@node1 ~]# virsh domifaddr vm1.0
 Name       MAC address          Protocol     Address
-------------------------------------------------------------------------------
 vnet0      52:54:00:e9:6e:43    ipv4         192.168.124.69/24
```

Connect to the vm using `ssh`:

```
[root@node0 ~]# ssh 192.168.124.69
root@192.168.124.69's password:
Activate the web console with: systemctl enable --now cockpit.socket

Last login: Sat Apr 17 14:08:17 2021 from 192.168.124.1
[root@localhost ~]#
```

We'll use address 10.0.0.11 for this system:

```
ip addr add 10.0.0.11/24 dev eth1
ip link set eth1 up
```

### Verify connectivity

At this point, our setup is complete. On `vm0.0`, we can connect to
`vm1.1` over the overlay network. For example, we can ping the remote
host:

```
[root@localhost ~]# ping -c2 10.0.0.11
PING 10.0.0.11 (10.0.0.11) 56(84) bytes of data.
64 bytes from 10.0.0.11: icmp_seq=1 ttl=64 time=1.79 ms
64 bytes from 10.0.0.11: icmp_seq=2 ttl=64 time=0.719 ms

--- 10.0.0.11 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1002ms
rtt min/avg/max/mdev = 0.719/1.252/1.785/0.533 ms
```

Or connect to it using `ssh`:

```
[root@localhost ~]# ssh 10.0.0.11 uptime
root@10.0.0.11's password:
 14:21:33 up  1:18,  1 user,  load average: 0.00, 0.00, 0.00
```

Using `tcpdump`, we can verify that these connections are going over
the overlay network. Let's watch for VXLAN traffic on `node1` by
running the following command (VXLAN is a UDP protocol running on port
4789)

```
tcpdump -i eth0 -n port 4789
```

When we run `ping -c2 10.0.0.11` on `vm0.0`, we see the following:

```
14:23:50.312574 IP 192.168.122.107.52595 > 192.168.122.174.vxlan: VXLAN, flags [I] (0x08), vni 0
IP 10.0.0.10 > 10.0.0.11: ICMP echo request, id 4915, seq 1, length 64
14:23:50.314896 IP 192.168.122.174.59510 > 192.168.122.107.vxlan: VXLAN, flags [I] (0x08), vni 0
IP 10.0.0.11 > 10.0.0.10: ICMP echo reply, id 4915, seq 1, length 64
14:23:51.314080 IP 192.168.122.107.52595 > 192.168.122.174.vxlan: VXLAN, flags [I] (0x08), vni 0
IP 10.0.0.10 > 10.0.0.11: ICMP echo request, id 4915, seq 2, length 64
14:23:51.314259 IP 192.168.122.174.59510 > 192.168.122.107.vxlan: VXLAN, flags [I] (0x08), vni 0
IP 10.0.0.11 > 10.0.0.10: ICMP echo reply, id 4915, seq 2, length 64
```

In the output above, we see that each packet in the transaction
results in two lines of output from `tcpdump`:

```
14:23:50.312574 IP 192.168.122.107.52595 > 192.168.122.174.vxlan: VXLAN, flags [I] (0x08), vni 0
IP 10.0.0.10 > 10.0.0.11: ICMP echo request, id 4915, seq 1, length 64
```

The first line shows the contents of the VXLAN packet, while the
second lines shows the data that was encapsulated in the VXLAN packet.

## That's all folks

We've achieved our goal: we have two virtual machines on two different
hosts communicating over a VXLAN overlay network. If you were to do
this "for real", you would probably want to make a number of changes:
for example, the network configuration we've applied in many cases
will not persist across a reboot; handling persistent network
configuration is still very distribution dependent, so I've left it
out of this post.
