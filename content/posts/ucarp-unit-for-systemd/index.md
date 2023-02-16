---
categories: [tech]
aliases: ["/2013/02/21/ucarp-unit-for-systemd/"]
title: A systemd unit for ucarp
date: "2013-02-21"
---

In Fedora 17 there are still a number of services that either have not
been ported over to `systemd` or that do not take full advantage of
`systemd`.  I've been investigating some IP failover solutions
recently, including [ucarp][], which includes only a System-V style
init script.

I've created a [template service][template] for ucarp that will let
you start a specific virtual ip like this:

    systemctl start ucarp@001

This will start ucarp using settings from `/etc/ucarp/vip-001.conf`.
The unit file is [on github][github] and embedded here for your
reading pleasure:

    [Unit]
    Description=UCARP virtual interface %I
    After=network.target

    [Service]
    Type=simple
    EnvironmentFile=-/etc/ucarp/vip-common.conf
    EnvironmentFile=-/etc/ucarp/vip-%I.conf
    ExecStart=/usr/sbin/ucarp -i $BIND_INTERFACE -p $PASSWORD -v %I -a $VIP_ADDRESS -s $SOURCE_ADDRESS $OPTIONS -u $UPSCRIPT -d $DOWNSCRIPT
    KillMode=control-group

    [Install]
    WantedBy=multiuser.target

[ucarp]: http://www.pureftpd.org/project/ucarp
[template]: http://0pointer.de/blog/projects/instances.html
[github]: https://gist.github.com/larsks/5009872

