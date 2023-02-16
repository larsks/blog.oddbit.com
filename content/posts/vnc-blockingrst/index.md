---
categories: [tech]
aliases: ["/2010/02/04/vnc-blockingrst/"]
title: Blocking VNC with iptables
date: "2010-02-04"
tags:
  - linux
  - classification
  - iptables
  - rfb
  - netfilter
  - vnc
---

VNC clients use the [RFB protocol][1] to provide virtual display capabilities. The RFB protocol, as implemented by most clients, provides very poor authentication options. While passwords are not actually sent "in the clear", it is possible to brute force them based on information available on the wire. The RFB 3.x protocol limits passwords to a maximum of eight characters, so the potential key space is relatively small.

It's possible to securely connect to a remote VNC server by tunneling your connection using ssh port forwarding (or setting up some sort of SSL proxy). However, while this ameliorates the password problem, it still leaves a VNC server running that, depending on the local system configuration, may accept connections from all over the world. This leaves open the possibility that someone could brute force the password and gain access to the systsem. The problem is exacerbated if a user is running a passwordless VNC session.

My colleague and I looked into the options for blocking VNC connections using layer 7 packet classification. This means identifying the protocol in use by inspecting packet payloads, rather than relying exclusively on port numbers (this prevents clever or malicious users from circumventing the restrictions by running a service on a non-standard port). Unfortunately, the actual [l7 netfilter module][2] is not available in CentOS (or Fedora). But wait, all is not lost!

First, a brief digression into the RFB protocol used by VNC. After completing a standard TCP handshake, the client and server engage in a RFB handshake. The server first sents the string "RFB " followed by the RFB protocol version supported by the server. The client responds with a similar message.

The initial handshake packet from the server:
    
    
    0000  00 00 0c 07 ac 34 00 21 86 14 e8 aa 08 00 45 00   .....4.!......E.
    0010  00 40 e8 b7 40 00 40 06 b6 51 8c f7 34 e0 62 76   .@..@.@..Q..4.bv
    0020  77 61 17 0d da ad ae 06 16 3f 22 48 92 cc 80 18   wa.......?"H....
    0030  00 5b 9b e1 00 00 01 01 08 0a e8 b1 fe 88 24 f1   .[............$.
    0040  e3 56 52 46 42 20 30 30 33 2e 30 30 38 0a         .VRFB 003.008.
    

And the response from the client:
    
    
    0000  00 21 86 14 e8 aa 00 1a 30 4d 0c 00 08 00 45 40   .!......0M....E@
    0010  00 40 e7 15 40 00 34 06 c3 b3 62 76 77 61 8c f7   .@..@.4...bvwa..
    0020  34 e0 da ad 17 0d 22 48 92 cc ae 06 16 4b 80 18   4....."H.....K..
    0030  ff ff 20 56 00 00 01 01 08 0a 24 f1 e3 57 e8 b1   .. V......$..W..
    0040  fe 88 52 46 42 20 30 30 33 2e 30 30 38 0a         ..RFB 003.008.
    

Ergo: if we can match the string "RFB " at the beginning of the TCP payload on inbound packets, we have a reliable way of blocking VNC packets ergardless of port.

Looking through the iptables man page, we find:
    
    
    u32
        U32  tests  whether quantities of up to 4 bytes extracted from
        a packet have specified values. The specification of what to
        extract is  general enough to find data at given offsets from
        tcp headers or payloads.
    

This looks especially appropriate, since our target match is exactly four bytes. Unfortunately, the syntax of the u32 module is a little baroque:
    
    
    Example:
    
           match IP packets with total length >= 256
           The IP header contains a total length field in bytes 2-3.
    
           --u32 "0 & 0xFFFF = 0x100:0xFFFF"
    

Fortunately, the internet is our friend:

> [http://www.stearns.org/doc/iptables-u32.v0.1.7.html][3]

This document provides a number of recipes designed for use with u32 module, including one that matches content at the beginning of the TCP payload. This gives us, ultimately:
    
    
    iptables -A INPUT -p tcp \
      -m connbytes --connbytes 0:1024 \
        --connbytes-dir both --connbytes-mode bytes \
      -m state --state ESTABLISHED \
      -m u32 --u32 "0>>22&0x3C@ 12>>26&0x3C@ 0=0x52464220" \
      -j REJECT --reject-with tcp-reset
    

This means:

- Match tcp packets only (-p tcp)
- Match only during the first 1024 bytes of the connection (-m connbytes --connbytes 0:1024 --connbytes-dir both --connbytes-mode bytes)
- Match only ESTABLISHED connections (-m state --state ESTABLISHED)
- Match bytes "0x52464240" ("RFB ") at the beginning of the TCP payload (-m u32 --u32 "0>>22&0x3C@ 12>>26&0x3C@ 0=0x52464220")
- Upon a match, force-close the connection with a RST packet. (-j REJECT --reject-with tcp-reset)

With this rule in place, all unenrypted VNC connections will be forcefully disconnected by the server.

Our original plan had been to try redirecting VNC traffic so that we could display a big "DON'T DO THAT" message, but this isn't possible -- by the time we match the client payload, the connection has already been established and is not amendable to redirection.

# Update

We modified this rule to use the iptables string module to make the match more specific to further reduce the chances of false positives. The rule now looks like this:
    
    
    iptables -A INPUT -p tcp \
      -m connbytes --connbytes 0:1024 \
        --connbytes-dir both --connbytes-mode bytes \
      -m state --state ESTABLISHED \
      -m u32 --u32 "0>>22&0x3C@ 12>>26&0x3C@ 0=0x52464220" \
      -m string --algo kmp --string "RFB 003." --to 130 \
      -j REJECT --reject-with tcp-reset
    

We thought about using the string module exclusively, but unlike the u32 module it is not possible to anchor the string match to the beginning of the TCP payload (since the ip and tcp headers may both be variable length).

[1]: http://www.realvnc.com/docs/rfbproto.pdf
[2]: http://l7-filter.sourceforge.net/
[3]: http://www.stearns.org/doc/iptables-u32.v0.1.7.html

