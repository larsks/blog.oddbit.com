---
aliases:
- /2015/06/26/openstack-networking-without-dhcp/
- /post/2015-06-26-openstack-networking-without-dhcp
categories:
- tech
date: '2015-06-26'
tags:
- openstack
- nova
- neutron
- cloud-init
title: OpenStack Networking without DHCP
---

In an OpenStack environment, [cloud-init][] generally fetches
information from the metadata service provided by Nova.  It also has
support for reading this information from a *configuration drive*,
which under OpenStack means a virtual CD-ROM device attached to your
instance containing the same information that would normally be
available via the metadata service.

[cloud-init]: https://cloudinit.readthedocs.org/en/latest/

It is possible to generate your network configuration from this
configuration drive, rather than relying on the DHCP server provided
by your OpenStack environment.  In order to do this you will need to
make the following changes to your Nova configuration:

1. You must be using a subnet that does have a DHCP server.  This
   means that you have created it using `neutron subnet-create
   --disable-dhcp ...`, or that you disabled DHCP on an existing
   network using `neutron net-update --disable-dhcp ...`.

1. You must set `flat_inject` to `true` in `/etc/nova/nova.conf`.
   This causes Nova to embed network configuration information in the
   meta-data embedded on the configuration drive.

1. You must ensure that `injected_network_template` in
   `/etc/nova/nova.conf` points to an appropriately formatted
   template.

Cloud-init expects the network configuration information to be
presented in the format of a Debian `/etc/network/interfaces` file,
even if you're using it on RHEL (or a derivative).  The template is
rendered using the [Jinja2][] template engine, and receives a
top-level key called `interfaces` that contains a list of
dictionaries, one for each interface.

A template similar to the following ought to be sufficient:

    {% for interface in interfaces %}
    auto {{ interface.name }}
    iface {{ interface.name }} inet static
      address {{ interface.address }}
      netmask {{ interface.netmask }}
      broadcast {{ interface.broadcast }}
      gateway {{ interface.gateway }}
      dns-nameservers {{ interface.dns }}
    {% endfor %}

This will directly populate `/etc/network/interfaces` on an Ubuntu
system, or will get translated into
`/etc/sysconfig/network-scripts/ifcfg-eth0` on a RHEL system (a RHEL
environment can only configure a single network interface using this
mechanism).

[jinja2]: http://jinja.pocoo.org/docs/dev/