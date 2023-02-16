---
categories: [tech]
aliases: ["/2014/05/19/flat-networks-with-ml-and-open/"]
title: Flat networks with ML2 and OpenVSwitch
date: "2014-05-19"
tags:
- openvswitch
- openstack
- neutron
---

Due to an unfortunate incident involving sleep mode and an overheated
backpack I had the "opportunity" to rebuild my laptop.  Since this meant
reinstalling OpenStack I used this as an excuse to finally move to the ML2
network plugin for Neutron.

I was attempting to add an external network using the normal incantation:

    neutron net-create external -- --router:external=true \
	    --provider:network_type=flat \
	    --provider:physical_network=physnet1

While this command completed successfully, I was left without any
connectivity between `br-int` and `br-ex`, despite having in my
`/etc/neutron/plugins/ml2/ml2_conf.ini`:

    [ml2_type_flat]
    flat_networks = *

    [ovs]
    network_vlan_ranges = physnet1
    bridge_mappings = physnet1:br-ex

The reason this is failing is very simple, but not terribly clear from
the existing documentation.  This is how the `neutron-server` process
is running:

    /usr/bin/python /usr/bin/neutron-server \
      --config-file /usr/share/neutron/neutron-dist.conf \
      --config-file /etc/neutron/neutron.conf \
      --config-file /etc/neutron/plugin.ini \
      --log-file /var/log/neutron/server.log

This is how the `neutron-openvswitch-agent` process is running:

    /usr/bin/python /usr/bin/neutron-openvswitch-agent \
      --config-file /usr/share/neutron/neutron-dist.conf \
      --config-file /etc/neutron/neutron.conf \
      --config-file /etc/neutron/plugins/openvswitch/ovs_neutron_plugin.ini \
      --log-file /var/log/neutron/openvswitch-agent.log

Note in particular that `neutron-server` is looking at
`/etc/neutron/plugin.ini`, which is a symlink to
`/etc/neutron/plugins/ml2/ml2_conf.ini`, while
`neutron-openvswitch-agent` is looking explicitly at 
`/etc/neutron/plugins/openvswitch/ovs_neutron_plugin.ini`.  The
physical network configuration needs to go into the
`ovs_neutron_plugin.ini` configuration file.

