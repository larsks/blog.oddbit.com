---
categories:
- tech
date: '2020-07-30T00:00:00Z'
filename: 2020-07-30-openshift-and-cnv-part-1-worki.md
tags:
- openshift
- cnv
- openshift-and-cnv
title: 'OpenShift and CNV: Installer network requirements'

---

This is the first in a [series of posts][] about my experience working
with [OpenShift][] and [CNV][] ("Container Native Virtualization", a
technology that allows you to use OpenShift to manage virtualized
workloads in addition to the containerized workloads for which
OpenShift is known). In this post, I'll be taking a look at the
installation experience, and in particular at how restrictions in our
local environment interacted with the network requirements of the installer.

[series of posts]: /tag/openshift-and-cnv
[openshift]: https://www.openshift.com/
[cnv]: https://www.redhat.com/en/topics/containers/what-is-container-native-virtualization

{{< toc >}}

## Overview

We're installing OpenShift on baremetal hosts using the IPI installer.
"IPI" stands for "Installer Provisioned Infrastructure", which means
that the OpenShift installer is responsible for provisioning an
operating system onto your hardware and managing the system
configuration. This is in contrast to UPI ("User Provisioned
Infrastructure"), in which you pre-provision the hosts using whatever
tools you're comfortable with and then point the installer and the
hardware once things are up and running.

In the environment I'm working with, we had a few restrictions that I
suspect are relatively common:

- The network we were using as our "baremetal" network (for the
  purposes of this article you can read that as "public" network) does
  not have a dynamic pool of leases. There is DHCP, but all addresses
  are statically assigned.

- Both the installer and the [Metal3][] service use [IPMI][] to manage
  the power of the OpenShift nodes. Access to our IPMI network
  requires that a static route exist on the host.

- Access to the IPMI network also requires a firewall exception for
  the host IP address.

[metal3]: https://metal3.io/
[ipmi]: https://en.wikipedia.org/wiki/Intelligent_Platform_Management_Interface

When you're reading through the installer documentation, the above
requirements don't seem problematic at first. Looking at the
[network requirements][], you'll see that the install calls for static
addressing of all the hardware involved in the install:

[network requirements]: https://openshift-kni.github.io/baremetal-deploy/4.4/Deployment.html#network-requirements_ipi-install-prerequisites

> Reserving IP Addresses for Nodes with the DHCP Server
>
> For the baremetal network, a network administrator must reserve a
> number of IP addresses, including:
> 
> 1. Three virtual IP addresses.
> 
>    - 1 IP address for the API endpoint
> 
>    -  1 IP address for the wildcard ingress endpoint
> 
>    -  1 IP address for the name server
> 
> 1. One IP Address for the Provisioning node.
> 
> 1. One IP address for each Control Plane (Master) node.
> 
> 1. One IP address for each worker node.

The "provisioning node" is the host on which you run the OpenShift
installer. What the documentation fails to mention is that the
services that manage the install don't actually run on the
provisioning node itself: instead, the installer starts up a
"bootstrap virtual machine" on the provisioning node, and manages the
install from there.

## The problem

The bootstrap vm is directly attached to both the baremetal and the
provisioning networks. It is created with a random MAC address, and
relies on DHCP for configuring the baremetal interface. This means
that:

- It's not possible to create a static DHCP lease for it, since you
  don't know the MAC address ahead of time.

- Since you can't create a static DHCP lease, you can't give it a
  static IP address.

- Since you can't give it a static IP address, you can't create a
  firewall exception for access to the IPMI network.

- And lastly, since you can't create a static DHCP lease, you can't
  conveniently use DHCP to assign the static route to the IPMI
  network.

This design decision -- the use of a bootstrap vm with a random MAC
address and no facility for assigning a static ip address -- is what
complicated our lives when we first set out to install OpenShift.

I'd like to emphasize that other than the issues discussed in the
remainder of this article, the install process has been relatively
smooth. We're able to go from zero to a completely installed OpenShift
cluster in just a few hours. There were some documentation issues
early on, but I think most of those have already been resolved.

## Attempted solution #1

OpenShift uses [Ignition][] for performing host configuration tasks.
If you're familiar with [cloud-init][], Ignition is doing something
very similar. One of the first things we tried was passing in a static
network configuration using Ignition. By running
`openshift-baremetal-install create ignition-configs`, it's possible
to modify the ignition configuration passed into the bootstrap vm.
Unfortunately, it turns out that prior to loading the ignition
configuration, the bootstrap vm image will attempt to configure all
system interfaces using DHCP...and if it fails to acquire any
addresses, it just gives up.

In that case, it never gets as far as attempting to apply the ignition
configuration, so this option didn't work out.

## Attempted solution #2

It is possible to pass a static ip configuration into the bootstrap vm
by modifying the kernel command line parameters. There are several
steps involved in creating a custom image:

- Parse through a JSON file to get URLs for the relevant images
- Download the images
- Uncompress the bootstrap image
- Use `virt-edit` to modify the grub configuration
- Calculate the uncompressed image checksum
- Re-compress the image

This also requires configuring your `install-config.yaml` to use the
new image, and finding an appropriate place to host it.

This mechanism *does* work, but there are a lot of moving parts and in
particular it seems like modifying the grub configuration could be a
little tricky if the command line in the original image were to change
in unexpected ways.

## How we actually solved the problem

We ended up taking advantage of the fact that while we didn't know the
MAC address ahead of time, we *did* know the MAC address *prefix*
ahead of time, so we created a small dynamic range (6 addresses)
limited to that MAC prefix (which would match pretty much anything
started by libvirt, but the only libvirt managed virtual machines
attached to this network were OpenShift bootstrap vms). We were able
to (a) attach the static route declaration to this small dynamic
range, and (b) grant firewall exceptions for these specific addresses.
The relevant lines in our [dnsmasq][] configuration look something like:

[dnsmasq]: http://www.thekelleys.org.uk/dnsmasq/doc.html

```
dhcp-host=52:54:00:*:*:*,set:libvirt,set:ocp
dhcp-range=tag:libvirt,10.1.2.130,10.1.2.135,255.255.255.0
dhcp-option=tag:ocp,option:classless-static-route,10.0.0.0/19,10.1.2.101
```
It's not perfect, but it's working fine.

[ignition]: https://github.com/coreos/ignition
[cloud-init]: https://cloudinit.readthedocs.io/en/latest/

## What I would like to see

The baremetal installer should allow the deployer to pass in a
static address configuration for the bootstrap vm using the
`install-config.yaml` file. The bootstrap vm should continue to boot
even if it can't initially configure an interface using DHCP (one
should be able to disable that initial DHCP attempt).
