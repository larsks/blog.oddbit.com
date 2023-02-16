---
categories:
- tech
date: '2020-07-30T01:00:00Z'
filename: 2020-07-30-openshift-and-cnv-part-2-expos.md
tags:
- openshift
- cnv
- networking
- openshift-and-cnv
title: 'OpenShift and CNV: Exposing virtualized services'

---

This is the second in a [series of posts][] about my experience working
with [OpenShift][] and [CNV][].  In this post, I'll be taking a look
at how to expose services on a virtual machine once you've git it up
and running.

[series of posts]: /tag/openshift-and-cnv
[openshift]: https://www.openshift.com/
[cnv]: https://www.redhat.com/en/topics/containers/what-is-container-native-virtualization

{{< toc >}}

## TL;DR

Networking seems to be a weak area for CNV right now.  Out of the box,
your options for exposing a service on a virtual machine on a public
address at a well known port are slim.

## Overview

We're hoping to use OpenShift + CNV as an alternative to existing
hypervisor platforms, primarily to reduce the number of complex,
distributed projects we need to manage. If we can have a single
control plane for both containerized and virtualized workloads, it
seems like a win for everyone.

In order to support the most common use case for our virtualization
platforms, consumers of this service need to be able to:

- Start a virtual machine using an image of their choice
- Expose services on that virtual machine using well-known ports
  on a routeable ip address

All of the above should be self service (that is, none of those steps
should requiring opening a support ticket or otherwise require
administrative assistance).

## Connectivity options

There are broadly two major connectivity models available to CNV
managed virtual machines:

- [Direct attachment to a host network](#direct-attachment)

- [Using an OpenShift Service](#using-an-openshift-service)

We're going to start with the direct attachment model, since this may
be familiar to people coming to CNV from other hypervisor platforms.

## Direct attachment

With a little configuration, it is possible to attach virtual machines
directly to an existing layer two network.

When running CNV, you can affect the network configuration of your
OpenShift hosts by creating `NodeNetworkConfigurationPolicy`
objects. Support for this is provided by `nmstate`, which is packaged
with CNV. For details, see "[Updating node network configuration][]" in
the OpenShift documentation.

For example, if we want to create a bridge interface on our nodes to
permit CNV managed virtual machines to attach to the network
associated with interface `eth1`, we might submit the following
configuration:

[updating node network configuration]: https://docs.openshift.com/container-platform/4.4/cnv/cnv_node_network/cnv-updating-node-network-config.html

```
apiVersion: nmstate.io/v1alpha1
kind: NodeNetworkConfigurationPolicy
metadata:
  name: br-example-policy
spec:
  nodeSelector:
    node-role.kubernetes.io/worker: ""
  desiredState:
    interfaces:
      - name: br-example
        type: linux-bridge
        state: up
        ipv4:
          dhcp: true
          enabled: true
        bridge:
          options:
            stp:
              enabled: false
          port:
            - name: eth1
```

This would create a Linux bridge device `br-example` with interface
`eth1` as a member. In order to expose this bridge to virtual
machines, we need to create a `NetworkAttachmentDefinition` (which can
be abbreviated as `net-attach-def`, but not as `nad` for reasons that
may be obvious to English speakers or readers of Urban Dictionary).

```
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: example
  namespace: default
spec:
  config: >-
    {
      "name": "example",
      "cniVersion": "0.3.1",
      "plugins": [
        {
          "type": "cnv-bridge",
          "bridge": "br-example",
          "ipam": {}
        },
        {
          "type": "cnv-tuning"
        }
      ]
    }
```

Once you have the above definitions in place, it's easy to select this
network when adding interfaces to a virtual machine. Actually making
use of these connections can be a little difficult.

In a situation that may remind of you of [some issues we had with the
installer][part1], your virtual machine will boot with a randomly
generated MAC address. Under CNV, generated MAC addresses are
associated with `VirtualMachineInstance` resources, which represents
currently running virtual machines. Your `VirtualMachine` object is
effectively a template used to generate a new `VirtualMachineInstance`
each time it boots. Because the address is associated with the
*instance*, you get a new MAC address every time you boot the virtual
machine. That makes it very difficult to associate a static IP address
with your CNV managed virtual machine.

[part1]: {{< ref "openshift-and-cnv-part-1-worki" >}}

It is possible to manually assign a MAC address to the virtual machine
when you create, but now you have a bevy of new problems:

- Anybody who wants to deploy a virtual machine needs to know what a
  MAC address looks like (you laugh, but this isn't something people
  generally have to think about).

- You probably need some way to track MAC address allocation to avoid
  conflicts when everyone chooses `DE:AD:BE:EF:CA:FE`.

## Using an OpenShift Service

Out of the box, your virtual machines can attach to the default pod
network, which is private network that provides masqueraded outbound
access and no direct inbound access. In this situation, your virtual
machine behaves much more like a container from a network perspective,
and you have access to many of the same network primitives available
to pods. You access these mechanisms by creating an OpenShift
`Service` resource.

Under OpenShift, a `Service` is used to "expose an application running
on a set of `Pods` as a network service (from [the Kubernetes
documentation][k8s_service]". From the perspective of OpenShift, your
virtual machine is just another application running in a Pod, so we
can use Service resources to expose applications running on your
virtual machine.

In order to manage these options, you'll want to install the
`virtctl` client. You can grab an [upstream release][] from the
[kubevirt][] project, or you can [enable the appropriate
repositories][] and install the `kubevirt-virtctl` package.

[kubevirt]: https://github.com/kubevirt/kubevirt
[upstream release]: https://github.com/kubevirt/kubevirt/releases
[enable the appropriate repositories]: https://docs.openshift.com/container-platform/4.2/cnv/cnv_install/cnv-installing-virtctl.html

[k8s_service]: https://kubernetes.io/docs/concepts/services-networking/service/

### Exposing services on NodePorts

A `NodePort` lets you expose a service on a random port associated
with the ip addresses of your OpenShift nodes.  If you have a virtual
machine named `test-vm-1` and you want to access the SSH service on
port 22, you can use the `virtctl` command like this:

```
virtctl expose vm test-vm-1 --port=22 --name=myvm-ssh-np --type=NodePort
```

This will result in `Service` that looks like:

```
$ oc get service myvm-ssh-np
NAME         TYPE       CLUSTER-IP    EXTERNAL-IP   PORT(S)        AGE
myvm-ssh-np  NodePort   172.30.4.25   <none>        22:31424/TCP   42s
```

The `CLUSTER-IP` in the above output is a cluster internal IP address
that can be used to connect to your server from other containers or
virtual machines. The `22:31424/TCP` entry tells us that port `31424`
on our OpenShift hosts now maps to port `22` in our virtual machine.

You can connect to your virtual machine with an `ssh` command line
along the lines of:

```
ssh -p 31424 someuser@hostname.of.a.node
```

You can use the hostname of any node in your OpenShift cluster.

This is fine for testing things out, but it doesn't allow you to
expose services on a well known port, and the cluster administrator
may be uncomfortable with services like this using the ip addresses of
cluster hosts.

### Exposing services on cluster external IPso

It is possible to manually assign an external ip address to an
OpenShift service.  For example:

```
virtctl expose vm test-vm-1 --port 22 --name myvm-ssh-ext --external-ip 192.168.185.18
```

Which results in the follow service:

```
NAME           TYPE        CLUSTER-IP       EXTERNAL-IP     PORT(S)   AGE
myvm-ssh-ext   ClusterIP   172.30.224.127   192.168.185.18   22/TCP    47s
```
While this sounds promising at first, there are several caveats:

- We once again find ourselves needing to manually manage a pool of
  addresses.
- By default, assigning an external ip address requires cluster-admin
  privileges.
- Once an external ip is assigned to a service, OpenShift doesn't
  actually take care of configuring that address on any host
  interfaces: it is up to the local administrator to arrange for
  traffic to that address to arrive at the cluster.

The practical impact of setting an external ip on a service is to
instantiate netfilter rules equivalent to the following:

```
-d 192.168.185.18/32 -p tcp --dport 22 -j DNAT --to-destination 10.129.2.11:22
```

If you configure the address `192.168.185.18` on a host interface (or
otherwise arrange for traffic to that address to reach your host),
these rules take care of directing the connection to your virtual
machine.

### Exposing services using a LoadBalancer

Historically, OpenShift was designed to run in cloud environments such
as OpenStack, AWS, Google Cloud Engine, and so forth. These platforms
provide integrated load balancer mechanisms that OpenShift was able to
leverage to expose services. Creating a `LoadBalancer` service would
instruct the platform to (a) allocate an address, (b) create a load
balancer, and (c) direct traffic from the load balancer to the target
of your service.

We can request a `LoadBalancer` using `virtctl` like this:

```
virtctl expose vm test-vm-1 --port=22 --name=myvm-ssh-np --type=LoadBalancer
```

Unfortunately, OpenShift for baremetal hosts does not include a load
balancer out of the box. This is a shame, because the `LoadBalancer`
solution hits just about all of our requirements:

- It automatically assigns ip addresses from a configured pool, so
  consumers of the environment don't need to manage either ip- or
  MAC-address assignment on their own.

- It doesn't require special privileges or administrator intervention
  (other than for the initial configuration).

- It lets you expose services on ports of your choice, rather than
  random ports.

There are some solutions out there that will provide an integrated
load balancer implementation for your baremetal cluster.  I've looked
at:

- [keepalived-operator][]
- [metallb][]

[metallb]: https://metallb.universe.tf/
[keepalived-operator]: https://github.com/redhat-cop/keepalived-operator

I hope we see an integrated LoadBalancer mechanism available for OpenShift on
baremetal in a near-future release.
