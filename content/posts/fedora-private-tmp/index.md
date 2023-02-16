---
categories: [tech]
aliases: ["/2012/11/05/fedora-private-tmp/"]
title: Private /tmp directories in Fedora
date: "2012-11-05"
tags:
  - fedora
  - systemd
---

I ran into an odd problem the other day: I was testing out some
configuration changes for a web application by dropping files into
`/tmp` and pointing the application configuration at the appropriate
directory.  Everything worked out great when testing it by hand...but
when starting up the `httpd` service, the application behaved as if it
was unable to find any of the files in `/tmp`.

My first assumption was that had simply missed something obvious like
file permissions or that I had a typo in my configuration, but after
repeated checks and lots of testing it was obvious that something else
was going on.

Grasping at straws I took a close look at the `systemd` service file
for `httpd`, which looks like this:

    [Unit]
    Description=The Apache HTTP Server (prefork MPM)
    After=syslog.target network.target remote-fs.target nss-lookup.target

    [Service]
    Type=forking
    PIDFile=/var/run/httpd/httpd.pid
    EnvironmentFile=/etc/sysconfig/httpd
    ExecStart=/usr/sbin/httpd $OPTIONS -k start
    ExecReload=/usr/sbin/httpd $OPTIONS -t
    ExecReload=/bin/kill -HUP $MAINPID
    ExecStop=/usr/sbin/httpd $OPTIONS -k stop
    PrivateTmp=true

    [Install]
    WantedBy=multi-user.target

Browsing throught file the following line caught my eye:

    PrivateTmp=true

If you know about per-process namespaces in Linux, you're probably
saying "Ah-ha!".  If you *don't* know about per-process namespaces in
Linux...you should, because this is the foundation for all sorts of
things including Linux Containers ([LXC][]).  Here's some good
introductory reading:

- <http://lxr.free-electrons.com/source/Documentation/unshare.txt>
- <http://www.debian-administration.org/article/628/Per-Process_Namespaces>
- <http://glandium.org/blog/?p=217>

In short, with this configuration in place, the service gets it's very
own version of `/tmp` not shared with any other process.  While the
files I placed in `/tmp` were visible in *my* process, they didn't
exist from the point of view of Apache.

The fix in my case was to place the files somewhere other than `/tmp`.
One could also disable the `PrivateTmp` setting, but it's generally
turned on for reasons of security.

The `PrivateTmp` option is documented in [Changes in Fedora for System
Administrators][changes], and Dan Walsh discusses it briefly on
[his blog][].

[changes]: https://docs.fedoraproject.org/en-US/Fedora/17/html/Release_Notes/sect-Release_Notes-Changes_for_Sysadmin.html
[his blog]: http://danwalsh.livejournal.com/51459.html
[lxc]: http://lxc.sourceforge.net/

