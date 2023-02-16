---
categories: [tech]
aliases: ["/2014/05/20/fedora-and-ovs-bridge-interfac/"]
title: Fedora and OVS Bridge Interfaces
date: "2014-05-20"
tags:
- fedora
- openstack
- openvswitch
- networking
---

I run OpenStack on my laptop, and I've been chasing down a pernicious
problem with OVS bridge interfaces under both F19 and F20.  My
OpenStack environment relies on an OVS bridge device named `br-ex` for
external connectivity and for making services available to OpenStack
instances, but after rebooting, `br-ex` was consistently unconfigured,
which caused a variety of problems.

This is the network configuration file for `br-ex` on my system:

    DEVICE=br-ex
    DEVICETYPE=ovs
    TYPE=OVSBridge
    BOOTPROT=static
    IPADDR=192.168.200.1
    NETMASK=255.255.255.0
    ONBOOT=yes
    NM_CONTROLLED=no
    ZONE=openstack

Running `ifup br-ex` would also fail to configure the interface, but
running `ifdown br-ex; ifup br-ex` would configure things
appropriately.

I finally got fed up with this behavior and spent some time chasing
down the problem, and this is what I found:

- Calling `ifup br-ex` passes control to
  `/etc/sysconfig/network-scripts/ifup-ovs`.
- `ifup-ovs` calls the `check_device_down` function from
  `network-functions`, which looks like:

        check_device_down ()
        {
             [ ! -d /sys/class/net/$1 ] && return 0
             if LC_ALL=C ip -o link show dev $1 2>/dev/null | grep -q ",UP" ; then
                return 1
             else
                return 0
             fi
        }

This returns failure (=1) if the interface flags contain `,UP`.
Unfortunately, since information about this device is stored
persistently in `ovsdb`, the device is already `UP` when `ifup` is
called, which causes `ifup-ovs` to skip further device
configuration.  The logic that calls `check_device_down` looks like
this:

    if check_device_down "${DEVICE}"; then
            ovs-vsctl -t ${TIMEOUT} -- --may-exist add-br "$DEVICE" $OVS_OPTIONS \
            ${OVS_EXTRA+-- $OVS_EXTRA} \
            ${STP+-- set bridge "$DEVICE" stp_enable="${STP}"}
    else
            OVSBRIDGECONFIGURED="yes"
    fi

This sets `OVSBRIDGECONFIGURED` if it believes the device is `UP`,
which causes `ifup-ovs` to skip the call to `ifup-eth` to configure
the interface:

    if [ "${OVSBOOTPROTO}" != "dhcp" ] && [ -z "${OVSINTF}" ] && \
            [ "${OVSBRIDGECONFIGURED}" != "yes" ]; then
            ${OTHERSCRIPT} ${CONFIG}
    fi

I have found that the simplest solution to this problem is to disable
the logic that sets `OVSBRIDGECONFIGURED`, by changing this:

    else
            OVSBRIDGECONFIGURED="yes"
    fi

To this:

    else
            : OVSBRIDGECONFIGURED="yes"
    fi

With this change in place, `br-ex` is correctly configured after a
reboot.

