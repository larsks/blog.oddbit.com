---
aliases:
- /2014/12/02/starting-systemd-services-without-blocking/
- /post/2014-12-02-starting-systemd-services-without-blocking
categories:
- tech
date: '2014-12-02'
tags:
- systemd
title: Starting systemd services without blocking
---

Recently, I've been playing around with [Fedora Atomic and
Kubernetes][atomic-post].  I ran into a frustrating problem in which I
would attempt to start a service from within a script launched by
[cloud-init][], only to have have `systemctl` block indefinitely
because the service I was attempting to start was dependent on
`cloud-init` finishing first.

[atomic-post]: {{< ref "fedora-atomic-openstack-and-ku" >}}
[cloud-init]: http://cloudinit.readthedocs.org/

It turns out that `systemctl` has a flag meant exactly for this
situation:

       --no-block
           Do not synchronously wait for the requested operation to finish. If
           this is not specified, the job will be verified, enqueued and
           systemctl will wait until it is completed. By passing this
           argument, it is only verified and enqueued.

Replacing `systemctl start <service>` with `systemctl start --no-block
<service>` has solved that particular problem.
