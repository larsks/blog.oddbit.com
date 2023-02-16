---
aliases:
- /2016/05/19/connecting-another-vm-to-your-tripleo-qu/
- /post/2016-05-19-connecting-another-vm-to-your-tripleo-qu
categories:
- tech
date: '2016-05-19'
tags:
- openvswitch
- openstack
- tripleo
title: Connecting another vm to your tripleo-quickstart deployment
---

Let's say that you have set up an environment using
[tripleo-quickstart][] and you would like to add another virtual
machine to the mix that has both "external" connectivity ("external"
in quotes because I am using it in the same way as the quickstart does
w/r/t the undercloud) and connectivity to the overcloud nodes.  How
would you go about setting that up?

For a concrete example, let's presume you have deployed an environment
using the default tripleo-quickstart configuration, which looks like
this:

    overcloud_nodes:
      - name: control_0
        flavor: control

      - name: compute_0
        flavor: compute

    extra_args: >-
      --neutron-network-type vxlan
      --neutron-tunnel-types vxlan
      --ntp-server pool.ntp.org

    network_isolation: true

That gets you one controller, one compute node, and enables network
isolation.  When your deployment is complete, networking from the
perspective of the undercloud looks like this:

- `eth0` is connected to the host's `brext` bridge and gives the
  undercloud NAT access to the outside world.  The interface will have
  an address on the `192.168.23.0/24` network.

- `eth1` is connected to the host's `brovc` bridge, which is the
  internal network for the overcloud.  The interface is attached to
  the OVS bridge `br-ctlplane`.

  The `br-ctlplane` bridge has the address `192.0.2.1`.

And your overcloud environment probably looks something like this:

    [stack@undercloud ~]$ nova list
    +-------...+-------------------------+--------+...+--------------------+
    | ID    ...| Name                    | Status |...| Networks           |
    +-------...+-------------------------+--------+...+--------------------+
    | 32f6ec...| overcloud-controller-0  | ACTIVE |...| ctlplane=192.0.2.7 |
    | d98474...| overcloud-novacompute-0 | ACTIVE |...| ctlplane=192.0.2.8 |
    +-------...+-------------------------+--------+...+--------------------+

We want to set up a new machine that has the same connectivity as the
undercloud.

## Upload an image

Before we can boot a new vm we'll need an image; let's start with the
standard CentOS 7 cloud image.  First we'll download it:

    curl -O http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2

Let's add a root password to the image and disable [cloud-init][],
since we're not booting in a cloud environment:

    virt-customize -a CentOS-7-x86_64-GenericCloud.qcow2 \
      --root-password password:changeme \
      --run-command "yum -y remove cloud-init"

Now let's upload it to libvirt:

    virsh vol-create-as oooq_pool centos-7-cloud.qcow2 8G \
      --format qcow2 \
      --allocation 0
    virsh vol-upload --pool oooq_pool centos-7-cloud.qcow2 \
      CentOS-7-x86_64-GenericCloud.qcow2

## <a id="boot-the-vm">Boot the vm</a>

I like to boot from a copy-on-write clone of the image, so that I can
use the base image multiple times or quickly revert to a pristine
state, so let's first create that clone:

    virsh vol-create-as oooq_pool myguest.qcow2 10G \
      --allocation 0 --format qcow2 \
      --backing-vol centos-7-cloud.qcow2 \
      --backing-vol-format qcow2

And then boot our vm:
<a id="virt-install"></a>

    virt-install --disk vol=oooq_pool/myguest.qcow2,bus=virtio \
      --import \
      -r 2048 -n myguest --cpu host \
      --os-variant rhel7 \
      -w bridge=brext,model=virtio \
      -w bridge=brovc,model=virtio \
      --serial pty \
      --noautoconsole

The crucial parts of the above command are the two `-w ...` arguments,
which create interfaces attached to the named bridges.

We can now connect to the console and log in as `root`:

    $ virsh console myguest
    .
    .
    .
    localhost login: root
    Password:

We'll see that the system already has an ip address on the "external"
network:

    [root@localhost ~]# ip addr show eth0
    2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP qlen 1000
        link/ether 52:54:00:7f:5c:5a brd ff:ff:ff:ff:ff:ff
        inet 192.168.23.27/24 brd 192.168.23.255 scope global dynamic eth0
           valid_lft 3517sec preferred_lft 3517sec
        inet6 fe80::5054:ff:fe7f:5c5a/64 scope link 
           valid_lft forever preferred_lft forever

And we have external connectivity:

    [root@localhost ~]# ping -c1 google.com
    PING google.com (216.58.219.206) 56(84) bytes of data.
    64 bytes from lga25s40-in-f14.1e100.net (216.58.219.206): icmp_seq=1 ttl=56 time=20.6 ms

    --- google.com ping statistics ---
    1 packets transmitted, 1 received, 0% packet loss, time 0ms
    rtt min/avg/max/mdev = 20.684/20.684/20.684/0.000 ms

Let's give `eth1` an address on the ctlplane network:

    [root@localhost ~]# ip addr add 192.0.2.254/24 dev eth1
    [root@localhost ~]# ip link set eth1 up

Now we can access the undercloud:

    [root@localhost ~]# ping -c1 192.0.2.1
    PING 192.0.2.1 (192.0.2.1) 56(84) bytes of data.
    64 bytes from 192.0.2.1: icmp_seq=1 ttl=64 time=0.464 ms

    --- 192.0.2.1 ping statistics ---
    1 packets transmitted, 1 received, 0% packet loss, time 0ms
    rtt min/avg/max/mdev = 0.464/0.464/0.464/0.000 ms

As well as all of the overcloud hosts using their addresses on the
same network:

    [root@localhost ~]# ping -c1 192.0.2.1
    PING 192.0.2.1 (192.0.2.1) 56(84) bytes of data.
    64 bytes from 192.0.2.1: icmp_seq=1 ttl=64 time=0.464 ms

    --- 192.0.2.1 ping statistics ---
    1 packets transmitted, 1 received, 0% packet loss, time 0ms
    rtt min/avg/max/mdev = 0.464/0.464/0.464/0.000 ms

## Allocating an address using DHCP

In the above instructions we've manually assigned an ip address on the
ctlplane network.  This works fine for testing, but it could
ultimately prove problematic if neutron were to allocate the same
address to another overcloud host.  We can use neutron to configure a
static dhcp lease for our new host.

First, we need the MAC address of our guest:

    virthost$ virsh dumpxml myguest |
      xmllint --xpath '//interface[source/@bridge="brovc"]' -
    <interface type="bridge">
      <mac address="52:54:00:42:d6:c2"/>
      <source bridge="brovc"/>
      <target dev="tap9"/>
      <model type="virtio"/>
      <alias name="net1"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x04" function="0x0"/>
    </interface>

And then on the undercloud we run `neutron port-create` to create a
port and associate it with our MAC address:

    [stack@undercloud]$ neutron port-create --mac-address 52:54:00:42:d6:c2 ctlplane

Now if we run `dhclient` on our guest, it will acquire a lease from
the neutron-managed DHCP server:

    [root@localhost]# dhclient -d eth1
    Internet Systems Consortium DHCP Client 4.2.5
    Copyright 2004-2013 Internet Systems Consortium.
    All rights reserved.
    For info, please visit https://www.isc.org/software/dhcp/

    Listening on LPF/eth1/52:54:00:42:d6:c2
    Sending on   LPF/eth1/52:54:00:42:d6:c2
    Sending on   Socket/fallback
    DHCPREQUEST on eth1 to 255.255.255.255 port 67 (xid=0xc90c0ba)
    DHCPACK from 192.0.2.5 (xid=0xc90c0ba)
    bound to 192.0.2.9 -- renewal in 42069 seconds.

We can make this persistent by creating
`/etc/sysconfig/network-scripts/ifcfg-eth1`:

    [root@localhost]# cd /etc/sysconfig/network-scripts
    [root@localhost]# sed s/eth0/eth1/g ifcfg-eth0 > ifcfg-eth1
    [root@localhost]# ifup eth1
    Determining IP information for eth1... done.

[tripleo-quickstart]: https://github.com/openstack/tripleo-quickstart/
[cloud-init]: https://cloudinit.readthedocs.io/en/latest/