---
categories: [tech]
aliases: ["/2018/02/27/listening-for-connections-on-a/"]
title: Listening for connections on all ports/any port
date: "2018-02-27"
tags:
- networking
---

On [IRC][] -- and other online communities -- it is common to use a
"pastebin" service to share snippets of code, logs, and other
material, rather than pasting them directly into a conversation.
These services will typically return a URL that you can share with
others so that they can see the content in their browser.

One of my favorite pastebin services is [termbin.com][], because it
works from the command line using tools you probably already have
installed.  Termbin runs the [fiche][] service, which listens for TCP
connections on port 9999, reads any content that you provide, and then
returns a URL.  For example, if I wanted to share my `iptables`
configuration with someone I could just run:

    $ iptables-save | nc termbin.com 9999
    http://termbin.com/gjfp

Visiting <http://termbin.com/gjfp> would show the output of that
command.

It's very convenient, but I found myself wondering: would it be
possible to configure things such that a service like [fiche][]
could listen on *any* port?

I started by looking into [raw sockets][], but that turned out to be a
terrible idea.  The solution was actually much simpler: use an
iptables [REDIRECT][] rule to take all traffic to a given ip address
and redirect it to the [fiche][] service.  This requires that you have
a spare ip address to dedicate to this service, but it is otherwise
very easy.

First, we start the [fiche][] service:

    $ ./fiche
    [Fiche][STATUS] Starting fiche on Tue Feb 27 11:53:01 2018...
    [Fiche][STATUS] Domain set to: http://example.com.
    [Fiche][STATUS] Server started listening on port: 9999.
    ============================================================

And we add an additional address to one of our network interfaces.
I'm adding `192.168.1.250` to `eth0` on my local system:

    $ sudo ip addr add 192.168.1.250/32 dev eth0

Next, we create two firewall rules:

- One in the `nat` `PREROUTING` table, which will intercept traffic
  from external systems:

        $ sudo iptables -t nat -A PREROUTING -p tcp -d 192.168.1.250 -j REDIRECT --to-ports 9999

- One in the `nat` `OUTPUT` table, which will intercept any locally
  generated traffic:

        $ sudo iptables -t nat -A OUTPUT -p tcp -d 192.168.1.250 -j REDIRECT --to-ports 9999

These two rules will intercept any traffic -- on *any* port -- to
192.168.1.250 and redirect it to the [fiche][] service.

For example, using no port (`nc` on my system defaults to port `0`):

    $ echo hello | nc 192.168.1.250
    http://example.com/tfka

And any other port works as well:

    $ echo hello | nc 192.168.1.250 10
    http://example.com/0j0c

    $ echo hello | nc 192.168.1.250 80
    http://example.com/u4fq

This solution will work with any TCP service.  The service will need
to be listening on `INADDR_ANY` (`0.0.0.0`), because the `REDIRECT`
rule rewrites the destination address to "the primary address of the
incoming interface".

[irc]: https://en.wikipedia.org/wiki/Internet_Relay_Chat
[termbin.com]: http://termbin.com
[fiche]: https://github.com/solusipse/fiche
[raw sockets]: https://en.wikipedia.org/wiki/Network_socket#Raw_socket
[redirect]: http://ipset.netfilter.org/iptables-extensions.man.html#lbDM
