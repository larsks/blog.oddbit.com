---
categories: [tech]
aliases: ["/2014/01/19/show-ovs-externalids/"]
title: Show OVS external-ids
date: "2014-01-19"
tags:
- openstack
- openvswitch
---

This is just here as a reminder for me:

An OVS interface has a variety of attributes associated with it, including an
`external-id` field that can be used to associate resources outside of
OpenVSwitch with the interface.  You can view this field with the following
command:

    $ ovs-vsctl --columns=name,external-ids list Interface

Which on my system, with a single virtual instance, looks like this:

    # ovs-vsctl --columns=name,external-ids list Interface
    .
    .
    .
    name                : "qvo519d7cc4-75"
    external_ids        : {attached-mac="fa:16:3e:f7:75:b0", iface-id="519d7cc4-7593-4944-af7b-4056436f2d66", iface-status=active, vm-uuid="0330b084-03db-4d42-a231-2cd6ad89515b"}
    .
    .
    .

Note the information contained here:

- `attached-mac` is the MAC address of the device attached to this interface.
- `vm-uuid` is the libvirt UUID for the instance attached to this interface...
- ...which also happens to be the Nova UUID for the instance.

So we can pass that UUID to `virsh dumpxml`:

    $ virsh dumpxml 0330b084-03db-4d42-a231-2cd6ad89515b
    <domain type='kvm' id='150'>
      <name>instance-0000009c</name>
      <uuid>0330b084-03db-4d42-a231-2cd6ad89515b</uuid>
      <memory unit='KiB'>6144000</memory>
      <currentMemory unit='KiB'>6144000</currentMemory>
      <vcpu placement='static'>1</vcpu>
    .
    .
    .

Or to `nova show`:

    $ nova show 0330b084-03db-4d42-a231-2cd6ad89515b 
    +--------------------------------------+----------------------------------------------------------+
    | Property                             | Value                                                    |
    +--------------------------------------+----------------------------------------------------------+
    | OS-DCF:diskConfig                    | MANUAL                                                   |
    | OS-EXT-AZ:availability_zone          | nova                                                     |
    .
    .
    .

