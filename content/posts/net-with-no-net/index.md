---
categories: [tech]
aliases: ["/2013/01/28/net-with-no-net/"]
title: Systemd and the case of the missing network
date: "2013-01-28"
---

I was intrigued by [this post][sockact] on socket activated containers with `systemd`.  The basic premise is:

- `systemd` opens a socket on the host and listens for connections.
- When a client connections, `systemd` spawns a new container.
- The host `systemd` passes the connected socket to the container
  `systemd`.
- Services in the container receive these sockets from the container
  `systemd`.

This is a very neat idea, since it delegates all the socket listening
to the host and only spins up container and service resources when
necessary.

An interesting corollary to this is that the service container doesn't
actually need any networking: since the *host* is responsible for
opening the socket and listening for connections, and the container
receives an already connected socket, you can create containers that
have no network interfaces other than the loopback interface *and
still connect to them remotely*.

The example presented in [Lennarts article][sockact] will work just
fine if you change this:

    ExecStart=/usr/bin/systemd-nspawn -jbD /srv/mycontainer 3

To this:

    ExecStart=/usr/bin/systemd-nspawn --private-network -jbD /srv/mycontainer 3

After this change, if you connect to this container you'll see:

    # ip addr
    1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN 
        link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
        inet 127.0.0.1/8 scope host lo
        inet6 ::1/128 scope host 
           valid_lft forever preferred_lft forever

This opens up a variety of interesting possibilities for creating
"endpoint" containers that offer services over the network but are
able to limit the scope of a compromised service.  Because
`systemd-nspawn` has been designed as more of a convenice tool than a
full container solution, we'll need to wait for `libvirt` and `lxc` to
introduce this socket-passing feature before it's more than an
interesting idea.


[sockact]: http://0pointer.de/blog/projects/socket-activated-containers.html

