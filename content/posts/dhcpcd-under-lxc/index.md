---
categories: [tech]
aliases: ["/2013/02/01/dhcpcd-under-lxc/"]
title: Running dhcpcd under LXC
date: "2013-02-01"
---

I've been working with [Arch Linux][] recently, which uses [dhcpcd][]
as its default DHCP agent.  If you try booting Arch inside an [LXC][]
container, you will find that `dhcpcd` is unable to configure your
network interfaces.  Running it by hand you will first see the
following error:

    # dhcpcd eth0
    dhcpcd[492]: version 5.6.4 starting
    dhcpcd[492]: eth0: if_init: Read-only file system
    dhcpcd[492]: eth0: interface not found or invalid

This happens because `dhcpcd` is trying to modify a sysctl value.
Running `dhcpcd` under `strace` we see:

    open("/proc/sys/net/ipv4/conf/eth0/promote_secondaries", O_WRONLY|O_CREAT|O_TRUNC, 0666) = -1 EROFS (Read-only file system)

This happens because `/proc` is typically mounted read-only in a
container environment (to prevent the container from modifying things
that would potentially affect the host system).

We can use a "bind mount" to solve this problem.  A "bind mount"
allows you to mount part of a filesystem on another part of the
filesystem.  In this case, we're going to mask that value in `/proc`
by bind mounting a file on top of it.

- First, we create the file we'll use as a mask:

        # echo 0 > /var/tmp/promote_secondaries

- Then we mount in on top of the `/proc` entry:

        # mount -o bind /var/tmp/promote_secondaries \
            /proc/sys/net/ipv4/conf/eth0/promote_secondaries

And now that `/proc` value is "writable" from the perspective of
`dhcpcd`.  If we try to run `dhcpcd` now, we see:

    # dhcpcd eth0
    dhcpcd[770]: version 5.6.4 starting
    dhcpcd[770]: eth0: sending IPv6 Router Solicitation
    dhcpcd[770]: eth0: rebinding lease of 192.168.117.53
    dhcpcd[770]: eth0: acknowledged 192.168.117.53 from 192.168.117.1
    dhcpcd[770]: eth0: checking for 192.168.117.53
    dhcpcd[770]: eth0: sending IPv6 Router Solicitation
    dhcpcd[770]: eth0: leased 192.168.117.53 for 3600 seconds
    dhcpcd[770]: forked to background, child pid 796

If you are running `dhcpcd` via the `dhcpcd@.service` unit, then you
can automate this masking with the following service unit:

    [Unit]
    Description=Mask read-only /proc entries for %I.
    RequiredBy=dhcpcd@%I
    Before=dhcpcd@%I

    [Service]
    ExecStartPre=/bin/dd if=/proc/sys/net/ipv4/conf/%I/promote_secondaries \
      of=/var/tmp/promote_secondaries_%I
    ExecStart=/bin/mount -o bind /var/tmp/promote_secondaries_%I \
      /proc/sys/net/ipv4/conf/%I/promote_secondaries
    RemainAfterExit=yes
    ExecStop=/bin/unmount /proc/sys/net/ipv4/conf/%I/promote_secondaries

    [Install]
    WantedBy=multi-user.target

If you see...

    /usr/lib/dhcpcd/dhcpcd-hooks/30-hostname: line 17: /proc/sys/kernel/hostname: Read-only file system

...you may need to do something similar to mask the `kernel.hostname`
entry in `/proc`, although this will need to be done once rather than
per-interface. Alternatively, you can modify the hook script
responsible for setting the hostname
(`/usr/lib/dhcpcd/dhcpcd-hooks/30-hostname`).

[arch linux]: http://www.archlinux.org/
[dhcpcd]: http://roy.marples.name/projects/dhcpcd/
[lxc]: http://lxc.sourceforge.net/

