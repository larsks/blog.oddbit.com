---
categories:
- tech
date: '2020-08-10'
filename: 2020-08-10-mac-address-management-in-cnv.md
tags:
- openshift-and-cnv
- openshift
- virtualization
title: 'OpenShift and CNV: MAC address management in CNV 2.4'

---

This is part of a [series of posts][] about my experience working with
[OpenShift][] and [CNV][].  In this post, I'll look at how the
recently released CNV 2.4 resolves some issues in managing virtual
machines that are attached directly to local layer 2 networks

[series of posts]: /tag/openshift-and-cnv
[openshift]: https://www.openshift.com/
[cnv]: https://www.redhat.com/en/topics/containers/what-is-container-native-virtualization

In [an earlier post][part 2], I discussed some issues around the
management of virtual machine MAC addresses in CNV 2.3: in particular,
that virtual machines are assigned a random MAC address not just at
creation time but every time they boot. CNV 2.4 (re-)introduces [MAC
address pools][] to alleviate these issues. The high level description
reads:

> The KubeMacPool component provides a MAC address pool service for
> virtual machine NICs in designated namespaces.

In more specific terms, that means that if you enable MAC address
pools on a namespace, when you create create virtual machine network
interfaces they will receive a MAC address from the pool. This is
associated with the `VirtualMachine` resource, **not** the
`VirtualMachineInstance` resource, which means that the MAC address
will persist across reboots.

This solves one of the major pain points of using CNV-managed virtual
machines attached to host networks.

To enable MAC address pools for a given namespace, set the
`mutatevirtualmachines.kubemacpool.io` label to `allocate`:

```
oc label namespace <namespace> mutatevirtualmachines.kubemacpool.io=allocate
```

[mac address pools]: https://docs.openshift.com/container-platform/4.5/virt/virtual_machines/vm_networking/virt-using-mac-address-pool-for-vms.html
[part 2]: {{< ref "openshift-and-cnv-part-2-expos" >}}
