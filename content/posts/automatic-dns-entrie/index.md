---
categories: [tech]
aliases: ["/2013/10/04/automatic-dns-entrie/"]
title: Automatic hostname entries for libvirt domains
date: "2013-10-04"
tags:
  - libvirt
  - virtualization
---

Have you ever wished that you could use `libvirt` domain names as
hostnames?  So that you could do something like this:

    $ virt-install -n anewhost ...
    $ ssh clouduser@anewhost

Since this is something that would certainly make my life convenient,
I put together a small script called [virt-hosts][] that makes this
possible.  You can find [virt-hosts][] in my [virt-utils][] GitHub
repository:

- https://raw.github.com/larsks/virt-utils/master/virt-hosts

Run by itself, with no options, `virt-hosts` will scan through your
running domains for interfaces on the libvirt `default` network, look
up those MAC addresses up in the corresponding `default.leases` file,
and then generate a hosts file on `stdout` like this:

    $ virt-hosts
    192.168.122.221	compute-tmp0-net0.default.virt compute-tmp0.default.virt
    192.168.122.101	centos-0-net0.default.virt centos-0.default.virt
    192.168.122.214	controller-tmp-net0.default.virt controller-tmp.default.virt

Each address will be assigned the name
`<domain_name>-<interface_name>.<network_name>.virt`.  The first
interface on the network will also be given the alias
`<domain_name>.<network_name>.virt`, so a host with multiple
interfaces on the same network would look like this:

    $ virt-hosts
    192.168.122.221	host0-net0.default.virt host0.default.virt
    192.168.122.110	host0-net1.default.virt

Of course, this is only half the solution: having generated a hosts
file we need to put it somewhere where your system can find it.

An aside: incron
----------------

Both of the following solutions rely on [incron][], a tool that uses
the Linux [inotify][] subsystem to trigger scripts in reaction to
events on file and directories.  In this case, we'll be using `incron`
to monitor the dnsmasq `default.leases` file and firing off a script
when it changes.

You could accomplish the same thing using the `inotifywait` program
from the [inotify-tools][] package and a small wrapper script, or you
could hook up something to the libvirt events framework.

[inotify]: http://en.wikipedia.org/wiki/Inotify
[inotify-tools]: https://github.com/rvoicilas/inotify-tools/wiki

Using /etc/hosts
----------------

If you want to update your `/etc/hosts` file, you can place the
following into a script called `update-virt-hosts` (somewhere in
root's `PATH`) and run that via [incron][]:

    #!/bin/sh

    sed -i '/^# BEGIN VIRT HOSTS/,/^# END VIRT HOSTS/ d' /etc/hosts
    cat <<EOF >>/etc/hosts
    # BEGIN VIRT HOSTS
    $(virt-hosts)
    # END VIRT HOSTS
    EOF

Make sure you have `incron` installed, and add the following to
`/etc/incron.d/virt-hosts`:

    /var/lib/libvirt/dnsmasq/default.leases IN_MODIFY update-virt-hosts

This will cause `incron` to run your `update-virt-hosts` script
whenever it sees an `IN_MODIFY` event on the `default.leases` file.

[incron]: http://inotify.aiken.cz/?section=incron&page=about&lang=en

Using NetworkManager + dnsmasq
------------------------------

I am running NetworkManager with the `dnsmasq` dns plugin. I created
the file `/etc/NetworkManager/dnsmasq.d/virthosts` containing:

    addn-hosts=/var/lib/libvirt/dnsmasq/default.addnhosts

This will cause the `dnsmasq` process started by `NetworkManager` to
use that file as an additional hosts file.  I then installed the
`incron` package and dropped the following in
`/etc/incron.d/virt-hosts`:

    /var/lib/libvirt/dnsmasq/default.leases IN_MODIFY /usr/local/bin/virt-hosts -ur

This has `incron` listen for changes to the `default.leases` file, and
whenever it receives the `IN_MODIFY` event it runs `virt-hosts` with
the `-u` (aka `--update`) and `-r` (aka `--reload-dnsmasq`) flags.
Thef former causes `virt-hosts` to send output to
`/var/lib/libvirt/dnsmasq/default.addnhosts` instead of `stdout`, and
the latter does a `killall -HUP dnsmasq` after installing the new
hosts file.

[virt-hosts]: https://raw.github.com/larsks/virt-utils/master/virt-hosts
[virt-utils]: https://raw.github.com/larsks/virt-utils/

