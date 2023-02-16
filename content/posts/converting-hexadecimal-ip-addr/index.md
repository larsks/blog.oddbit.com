---
aliases:
- /2015/03/08/converting-hexadecimal-ip-addresses-to-dotted-quads-with-bas/
- /post/2015-03-08-converting-hexadecimal-ip-addresses-to-dotted-quads-with-bas
categories:
- tech
date: '2015-03-08'
tags:
- bash
- docker
title: Converting hexadecimal ip addresses to dotted quads with Bash
---

This is another post that is primarily for my own benefit for the next
time I forget how to do this.

I wanted to read routing information directly from `/proc/net/route`
using `bash`, because you never know what may or may not be available
in the minimal environment of a Docker container (for example, the
`iproute` package is not installed by default in the Fedora Docker
images).  The contents of `/proc/net/route` looks something like:

    Iface	Destination	Gateway 	Flags	RefCnt	Use	Metric	Mask		MTU	Window	IRTT                                                       
    eth0	00000000	0101A8C0	0003	0	0	1024	00000000	0	0	0                                                                          
    eth0	37E9BB42	0101A8C0	0007	0	0	20	FFFFFFFF	0	0	0                                                                            

If I want the address of the default gateway, I can trivially get the
hexadecimal form like this:

    awk '$2 == "00000000" {print $3}' /proc/net/route

Which gives me:

    0101A8C0

This is in little-endian order; that is, the above bytes represent `1
1 168 192`, which you may recognize better as `192.168.1.1`.  So, we
need to convert this into a sequence of individual octets, reverse the
order, and produce the decimal equivalent of each octet.

The following gives us the octets in the correct order, prefixed by
`0x` (which we're going to want in the next step):

    awk '$2 == "00000000" {print $3}' /proc/net/route |
      sed 's/../0x& /g' | tr ' ' '\n' | tac

We can put this into a bash array like this:

    octets=($(
    awk '$2 == "00000000" {print $3}' /proc/net/route |
      sed 's/../0x& /g' | tr ' ' '\n' | tac
    ))

And we convert those hexadecimal octets into decimal like this:

    printf "%d." ${octets[@]} | sed 's/\.$/\n/'

An interesting feature of the Bash `printf` command -- and one that
may be surprising to people who are coming from a C background -- is
that:

> The format is re-used as necessary to consume all of the arguments.

That means, that a command like this:

    printf "%d." 1 2 3 4

Will yield:

    1.2.3.4.

If we put this all together, we might end up with something like:

    hexaddr=$(awk '$2 == "00000000" {print $3}' /proc/net/route)
    ipaddr=$(printf "%d." $(
      echo $hexaddr | sed 's/../0x& /g' | tr ' ' '\n' | tac
      ) | sed 's/\.$/\n/')