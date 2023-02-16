---
aliases:
- /2015/03/09/diagnosing-problems-with-an-openstack-deplo/
- /post/2015-03-09-diagnosing-problems-with-an-openstack-deplo
categories:
- tech
date: '2015-03-09'
tags:
- openstack
title: Diagnosing problems with an OpenStack deployment
cover: lucy.jpg
---

I recently had the chance to help a colleague debug some problems in
his OpenStack installation.  The environment was unique because it was
booting virtualized [aarch64][] instances, which at the time did not
have any PCI bus support...which in turn precluded things like graphic
consoles (i.e., VNC or SPICE consoles) for the Nova instances.

[aarch64]: https://fedoraproject.org/wiki/Architectures/AArch64

This post began life as an email summarizing the various configuration
changes we made on the systems to get things up and running.  After
writing it, I decided it presented an interesting summary of some
common (and maybe not-so-common) issues, so I am posting it here in
the hopes that other folks will find it interesting.

## Serial console configuration

### The problem

We needed console access to the Nova instances in order to diagnose
some networking issues, but there was no VGA console support in the
virtual machines.  Recent versions of Nova provide serial console
support, but do not provide any client-side tool for *accessing* the
serial console.

We wanted to:

- Correctly configure Nova to provide serial console support, and
- Get the [novaconsole][] tool installed in order to access the serial
  consoles.

[novaconsole]: https://github.com/larsks/novaconsole

### Making novaconsole work

In order to get `novaconsole` installed we needed the
`websocket-client` library, which is listed in `requirements.txt` at
the top level of the `novaconsole` source.  Normally one would just
`pip install .` from the source directory, but `python-pip` was not
available on our platform.

That wasn't a big issue because we *did* have `python-setuptools`
available, so I was able to simply run (inside the `novaconsole`
source directory):

    python setup.py install

And now we had a `/usr/bin/novaconsole` script, and we were able to
use it like this to connect to the console of a nova instance named
"test0":

    novaconsole test0

(For this to work you need appropriate Keystone credentials loaded in
your environment.  You can also provide a websocket URL in lieu of an
instance name.)

### Configuration changes on the controller

The controller did not have the `openstack-nova-serialproxy` package
installed, which provides the `nova-serialproxy` service.  This service
provides the websocket endpoint used by clients, so without this
service you you won't be able to connect to serial consoles.

Installing the service was a simple matter of:

    yum -y install openstack-nova-serialproxy
    systemctl enable openstack-nova-serialproxy
    systemctl start openstack-nova-serialproxy

### Configuration changes on the compute nodes

We also need to enable the serial console support on our compute nodes,
and we need to change the following configuration options in
`nova.conf` in the `serial_console` section:

    # Set this to 'true' to enable serial console support.
    enabled=true

    # Enabling serial console support means that spawning an instance
    # causes qemu to open up a listening TCP socket for the serial
    # console.  This socket binds to the `listen` address.  It
    # defaults to 127.0.0.1, which will not permit a remote host --
    # such as your controller -- from connecting to the port.  Setting
    # this to 0.0.0.0 means "listen on all available addresses", which
    # is *usually* what you want.
    listen=0.0.0.0 

    # `proxyclient_address` is the address to which the
    # nova-serialproxy service will connect to access serial consoles
    # of instances located on this physical host.  That means it needs
    # to be an address of a local interface (and so this value will be
    # unique to each compute host).
    proxyclient_address=10.16.184.118

In a production deployment, we would also need to modify the
`base_url` option in this section, which is used to generate the URLs
provided via the `nova get-serial-console` command.  With the default
configuration, the URLs will point to 127.0.0.1, which is fine as long
as we are running `novaconsole` on the same host as
`nova-serialproxy`.

After making these changes, we need to restart nova-compute on all the
compute hosts:

    # openstack-service restart nova

*And* we will need to re-deploy any running instances, because they
will still have sockets listening on 127.0.0.1.

The network ports opened for the serial console service are controlled
by the `port_range` setting in the `serial_console` section.  We must
permit connections to these ports from our controller.  I added the
following rule with iptables:

    # iptables -I INPUT 1 -p tcp --dport 10000:20000 -j ACCEPT

In practice, we would probably want to limit this specifically to our
controller(s).

<!-- got this far -->

## Networking on the controller

### The problem

Nova instances were not successfully obtaining ip addresses from the
Nova-managed DHCP service.

### Selinux and the case of the missing interfaces

When I first looked at the system, it was obvious that something
fundamental was broken because the Neutron routers were missing
interfaces.

Each neutron router is realized as a network namespace on the
network host.  We can see these namespaces with the `ip netns`
command:

    # ip netns
    qrouter-42389195-c8c1-4d68-a16c-3937453f149d
    qdhcp-d2719d67-fd00-4620-be00-ea8525dc6524

We can use the `ip netns exec` command to run commands inside the
router namespace.  For instance, we can run the following to see a
list of network interfaces inside the namespace:

    # ip netns exec qrouter-42389195-c8c1-4d68-a16c-3937453f149d \
      ip addr show

For a router we would expect to see something like this:

    1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN 
        link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
        inet 127.0.0.1/8 scope host lo
           valid_lft forever preferred_lft forever
        inet6 ::1/128 scope host 
           valid_lft forever preferred_lft forever
    18: qr-b3cd13d6-94: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN 
        link/ether fa:16:3e:61:89:49 brd ff:ff:ff:ff:ff:ff
        inet 10.0.0.1/24 brd 10.0.0.255 scope global qr-b3cd13d6-94
           valid_lft forever preferred_lft forever
        inet6 fe80::f816:3eff:fe61:8949/64 scope link 
           valid_lft forever preferred_lft forever
    19: qg-89591203-47: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN 
        link/ether fa:16:3e:30:b5:05 brd ff:ff:ff:ff:ff:ff
        inet 172.24.4.231/28 brd 172.24.4.239 scope global qg-89591203-47
           valid_lft forever preferred_lft forever
        inet 172.24.4.232/32 brd 172.24.4.232 scope global qg-89591203-47
           valid_lft forever preferred_lft forever
        inet6 fe80::f816:3eff:fe30:b505/64 scope link 
           valid_lft forever preferred_lft forever

But all I found was the loopback interface:

    1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN 
        link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
        inet 127.0.0.1/8 scope host lo
           valid_lft forever preferred_lft forever
        inet6 ::1/128 scope host 
           valid_lft forever preferred_lft forever

After a few attempts to restore the router to health through API commands (such
as by clearing and re-setting the network gateway), I looked in the
logs for the `neutron-l3-agent` service, which is the service
responsible for configuring the routers.  There I found:

    2015-02-20 17:16:52.324 22758 TRACE neutron.agent.l3_agent Stderr:
    'Error: argument "qrouter-42389195-c8c1-4d68-a16c-3937453f149d" is
    wrong: Invalid "netns" value\n\n'

This is weird because clearly a network namespace with a matching name
was available.  When weird inexplicable errors happen, we often look
first to selinux, and indeed, running `audit2allow -a` showed us that
neutron was apparently missing a privilege:

    #============= neutron_t ==============
    allow neutron_t unlabeled_t:file { read open };

After putting selinux in permissive mode[^1] and restarting neutron
services, things looked a lot better.  To completely restart neutron,
I usually do:

    openstack-service stop neutron
    neutron-ovs-cleanup
    neutron-netns-cleanup
    openstack-service start neutron

The `openstack-service` command is a wrapper over `systemctl` or
`chkconfig` and `service` that operates on whatever openstack services
you have enabled on your host.  Providing a additional arguments
limits the action to services that match that name, so in addition to
`openstack-service stop neutron` you can do something like
`openstack-service stop nova glance` to stop all Nova and Glance
services, etc.

[^1]: ...as a temporary measure, pending opening a bug report to get
  things corrected so that this step would no longer be necessary.

### Iptables and the case of the missing packets

After diagnosing the selinux issue noted above, virtual networking
layer looked fine, but we still weren't able to get traffic between
the test instance and the router/dhcp server on the controller.  

Traffic was clearly traversing the VXLAN tunnels, as revealed by
running `tcpdump` on both ends of the tunnel (where 4789 is the vxlan
port):

    tcpdump -i eth0 -n port 4789

But that traffic was never reaching, e.g., the dhcp namespace.
Investigating the Open vSwitch (OVS) configuration on our host showed
that everything look correct; commands I use to look at things were:

- `ovs-vsctl show` to look at the basic layout of switches and
  interfaces,

- `ovs-ofctl dump-flows <bridge>` to look at the openflow rules
  associated with a particular OVS switch, and

- `ovs-dpctl-top`, which provides a top-like view of flow activity on
  the OVS bridges.

Ultimately, it turns out that there were some iptables rule missing
from our configuration.  On the host, looking for rules that match
vxlan traffic I found a single rule for vxlan traffic:

    # iptables -S | grep 4789
    -A INPUT -s 10.16.184.117/32 -p udp -m multiport --dports 4789 ...

The compute node we were operating with was 10.16.184.118 (which is
not the address listed in the above rule), so vxlan traffic from this
host was being rejected by the kernel.  I added a new rule to match
vxlan traffic from the compute host:

    # iptables -I INPUT 18 -s 10.16.184.118/32 -p udp -m multiport --dports 4789 ...

This seemed to take care of things, but it's a bit of a mystery why
this wasn't configured for us in the first place by the installer.
This may have been a bug in [packstack][]; we would need to do clean
re-deploy to verify this behavior.

[packstack]: https://wiki.openstack.org/wiki/Packstack

### Access to floating ip addresses

In order to access our instances using their floating ip addresses
from our host, we need a route to the floating ip network.  The
easiest way to do this in a test environment, if you are happy with
host-only networking, is to assign interface `br-ex` the address of
the default gateway for your floating ip network.  The default
floating ip network configured by `packstack` is 172.24.4.224/28, and
the gateway for that network is `172.24.24.225`.  We can assign this
address to `br-ex` like this:

    # ip addr add 172.24.4.225/28 dev br-ex

With this in place, connections to floating ips will route via br-ex,
which in turn is bridged to the external interface of your neutron
router.

Setting the address by hand like this means it will be lost next time
we reboot.  We can make this configuration persistent by modifying (or
creating)
`/etc/sysconfig/network-scripts/ifcfg-br-ex` so that it looks like this:

    DEVICE=br-ex
    DEVICETYPE=ovs
    TYPE=OVSBridge
    BOOTPROT=static
    IPADDR=172.24.4.225
    NETMASK=255.255.255.240
    ONBOOT=yes

If you're not able to map CIDR prefixes to dotted-quad netmasks in
your head, the `ipcalc` tool is useful:

    $ ipcalc -m 172.24.4.224/28
    NETMASK=255.255.255.240

## The state of things

With all the above changes in place, we had a functioning OpenStack
environment.

We could spawn an instance as the "demo" user:

    # . keystonerc_demo
    # nova boot --image "rhelsa" --flavor m1.small example

Create a floating ip address:

    # nova floating-ip-create public
    +--------------+-----------+----------+--------+
    | Ip           | Server Id | Fixed Ip | Pool   |
    +--------------+-----------+----------+--------+
    | 172.24.4.233 | -         | -        | public |
    +--------------+-----------+----------+--------+

Assign that address to our instance:

    # nova floating-ip-associate example 172.4.4.233

And finally we were able to access services on that instance (provided
that our security groups (and local iptables configuration on the
instance) permit access to that service).
