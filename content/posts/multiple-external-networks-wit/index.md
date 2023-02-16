---
categories: [tech]
aliases: ["/2014/05/28/multiple-external-networks-wit/"]
title: Multiple external networks with a single L3 agent
date: "2014-05-28"
tags:
- openstack
- neutron
- networking
---

In the old days (so, like, last year), Neutron supported a single
external network per L3 agent.  You would run something like this...

    $ neutron net-create external --router:external=true

...and neutron would map this to the bridge defined in
`external_network_bridge` in `/etc/neutron/l3_agent.ini`.  If you
wanted to support more than a single external network, you would need
to run multiple L3 agents, each with a unique value for
`external_network_bridge`.

There is now a better option available.

Assumptions
-----------

In this post, I'm assuming:

- You're using the ML2 plugin for Neutron.
- You're using the Open vSwitch mechanism driver for the ML2 plugin
- You have `eth1` and `eth2` connected directly to networks that you
  would like to make available as external networks in OpenStack.

Create your bridges
-------------------

For each external network you wish to support, create a new OVS
bridge.  For example, assuming that we want to make a network attached
to `eth1` and a network attached to `eth2` available to tenants:

    # ovs-vsctl add-br br-eth1
    # ovs-vsctl add-port br-eth1 eth1
    # ovs-vsctl add-br br-eth2
    # ovs-vsctl add-port br-eth2 eth2

Realistically, you would accomplish this via your system's native
network configuration mechanism, but I'm going to gloss over that
detail for now.

Configure the L3 Agent
----------------------

Start with the following comment in `l3_agent.ini`:

    # When external_network_bridge is set, each L3 agent can be associated
    # with no more than one external network. This value should be set to the UUID
    # of that external network. To allow L3 agent support multiple external
    # networks, both the external_network_bridge and gateway_external_network_id
    # must be left empty.

Following those instructions, make sure that both
`external_network_bridge` and `gateway_external_network_id` are unset
in `l3_agent.ini`.

Configure the ML2 Plugin
------------------------

We are creating "flat" networks in this example, so we need to make
sure that we can create flat networks.  Make sure that the
`type_drivers` parameter of the `[ml2]` section of your plugin
configuration includes `flat`:

    [ml2]
    type_drivers = local,flat,gre,vxlan

In the `[ml2_type_flat]` section, need to create a list of physical
network names that can be used to create flat networks.  If you want
all physical networks to be available for flat networks, you can use
`*`:

    [ml2_type_flat]
    flat_networks = *    

Both of these changes probably go in `/etc/neutron/plugin.ini`, but
*may* going elsewhere depending on how your system is configured.

Configure the Open vSwitch Agent
---------------------------------

For each bridge, you will need to add entries to both the
`network_vlan_ranges` and `bridge_mappings` parameters of the `[ovs]`
section of your plugin configuration.  For the purposes of this post,
that means:

    [ovs]
    network_vlan_ranges = physnet1,physnet2
    bridge_mappings = physnet1:br-eth1,physnet2:br-eth2

This will probably go in `/etc/neutron/plugin.ini`.  Specifically, it
needs to go wherever your `neutron-openvswitch-agent` process is
looking for configuration information.  So you if you see this:

    $ ps -fe | grep openvswitch-agent
    neutron  12529     1  0 09:50 ?        00:00:08 /usr/bin/python /usr/bin/neutron-openvswitch-agent --config-file /usr/share/neutron/neutron-dist.conf --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/openvswitch/ovs_neutron_plugin.ini --log-file /var/log/neutron/openvswitch-agent.log

...then you would make the changes to `/etc/neutron/plugins/openvswitch/ovs_neutron_plugin.ini`.

Restart Neutron
---------------

You will need to restart both the l3 agent and the openvswitch agent.
If you're on a recent Fedora/RHEL/CentOS, you can restart all Neutron
services like this:

    # openstack-service restart neutron

Inspect your Open vSwitch Configuration
---------------------------------------

As root, run `ovs-vsctl show`.  You should see something like this:

    f4a4312b-307e-4c3c-b728-9434000a34ff
        Bridge br-int
            Port br-int
                Interface br-int
                    type: internal
            Port "int-br-eth2"
                Interface "int-br-eth2"
            Port int-br-ex
                Interface int-br-ex
            Port "int-br-eth1"
                Interface "int-br-eth1"
        Bridge "br-eth2"
            Port "br-eth2"
                Interface "br-eth2"
                    type: internal
            Port "phy-br-eth2"
                Interface "phy-br-eth2"
            Port "eth2"
                Interface "eth2"
        Bridge "br-eth1"
            Port "br-eth1"
                Interface "br-eth1"
                    type: internal
            Port "phy-br-eth1"
                Interface "phy-br-eth1"
            Port "eth1"
                Interface "eth1"
        ovs_version: "2.0.1"

Here you can see the OVS bridge `br-eth1` and `br-eth2`, each with the
appropriate associated physical interface and links to the integration
bridge, `br-int`.

Create your external networks
-----------------------------

With admin credentials, use the `net-create` and `subnet-create`
commands to create the appropiate networks:

    $ neutron net-create external1 -- --router:external=true \
      --provider:network_type=flat \
      --provider:physical_network=physnet1
    +---------------------------+--------------------------------------+
    | Field                     | Value                                |
    +---------------------------+--------------------------------------+
    | admin_state_up            | True                                 |
    | id                        | 23f4b5f6-14fd-4bab-a8b0-445257bbc0d1 |
    | name                      | external1                            |
    | provider:network_type     | flat                                 |
    | provider:physical_network | physnet1                             |
    | provider:segmentation_id  |                                      |
    | router:external           | True                                 |
    | shared                    | False                                |
    | status                    | ACTIVE                               |
    | subnets                   |                                      |
    | tenant_id                 | 6f736b1361b74789a81d4d53d88be3c5     |
    +---------------------------+--------------------------------------+
    $ neutron subnet-create --disable-dhcp external1 10.1.0.0/24
    +------------------+--------------------------------------------+
    | Field            | Value                                      |
    +------------------+--------------------------------------------+
    | allocation_pools | {"start": "10.1.0.2", "end": "10.1.0.254"} |
    | cidr             | 10.1.0.0/24                                |
    | dns_nameservers  |                                            |
    | enable_dhcp      | False                                      |
    | gateway_ip       | 10.1.0.1                                   |
    | host_routes      |                                            |
    | id               | 363ba289-a989-4acb-ac3b-ffaeb90796fc       |
    | ip_version       | 4                                          |
    | name             |                                            |
    | network_id       | 23f4b5f6-14fd-4bab-a8b0-445257bbc0d1       |
    | tenant_id        | 6f736b1361b74789a81d4d53d88be3c5           |
    +------------------+--------------------------------------------+
    

    $ neutron net-create external2 -- --router:external=true \
      --provider:network_type=flat \
      --provider:physical_network=physnet2
    +---------------------------+--------------------------------------+
    | Field                     | Value                                |
    +---------------------------+--------------------------------------+
    | admin_state_up            | True                                 |
    | id                        | 762be5de-31a2-46b8-925c-0967871f8181 |
    | name                      | external2                            |
    | provider:network_type     | flat                                 |
    | provider:physical_network | physnet2                             |
    | provider:segmentation_id  |                                      |
    | router:external           | True                                 |
    | shared                    | False                                |
    | status                    | ACTIVE                               |
    | subnets                   |                                      |
    | tenant_id                 | 6f736b1361b74789a81d4d53d88be3c5     |
    +---------------------------+--------------------------------------+
    $ neutron subnet-create --disable-dhcp external2 10.2.0.0/24
    +------------------+--------------------------------------------+
    | Field            | Value                                      |
    +------------------+--------------------------------------------+
    | allocation_pools | {"start": "10.2.0.2", "end": "10.2.0.254"} |
    | cidr             | 10.2.0.0/24                                |
    | dns_nameservers  |                                            |
    | enable_dhcp      | False                                      |
    | gateway_ip       | 10.2.0.1                                   |
    | host_routes      |                                            |
    | id               | edffc5c6-0e16-4da0-8eba-9d79ab9fd2fe       |
    | ip_version       | 4                                          |
    | name             |                                            |
    | network_id       | 762be5de-31a2-46b8-925c-0967871f8181       |
    | tenant_id        | 6f736b1361b74789a81d4d53d88be3c5           |
    +------------------+--------------------------------------------+

This assumes that `eth1` is connected to a network using
`10.1.0.0/24` and `eth2` is connected to a network using
`10.2.0.0/24`, and that each network has a gateway sitting at the
corresponding `.1` address.

And you're all set!

