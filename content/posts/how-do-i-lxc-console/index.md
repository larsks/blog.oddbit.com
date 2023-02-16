---
categories: [tech]
aliases: ["/2013/01/28/how-do-i-lxc-console/"]
title: How do I LXC console?
date: "2013-01-28"
---

It took me an unreasonably long time to boot an LXC container with
working console access.  For the record:

When you boot an LXC container, the console appears to be attached to
a `pts` device.  For example, when booting with the console attached to
your current terminal:

    # lxc-start -n node0
    ...
    node0 login: root
    Last login: Mon Jan 28 16:35:19 on tty1
    [root@node0 ~]# tty
    /dev/console
    [root@node0 ~]# ls -l /dev/console
    crw------- 1 root tty 136, 12 Jan 28 16:36 /dev/console

This is also true when you attach to a container using `lxc-console`:

    # lxc-start -n node0 -d
    # lxc-console -n node0
    Type <Ctrl+a q> to exit the console

    node0 login: root
    Last login: Mon Jan 28 16:36:00 on console
    [root@node0 ~]# tty
    /dev/tty1
    [root@node0 ~]# ls -l /dev/tty1
    crw------- 1 root tty 136, 6 Jan 28 16:37 /dev/tty1

In both cases, the devices have major number `136`, which is the `pts`
driver.  This means that if your LXC configuration file has this:

    lxc.cgroup.devices.deny = a

Then your LXC configuration file will also need:

    lxc.cgroup.devices.allow = c 136:* rwm

