---
categories: [tech]
aliases: ["/2010/01/29/linux-upnp-gateway/"]
title: Linux UPnP Gateway
date: "2010-01-29"
tags:
  - networking
  - peertopeer
  - linux
  - upnp
---

Like many other folks out there, I have several computers in my house connected to the outside world via a Linux box acting as a NAT gateway. I often want to use application such as BitTorrent and Freenet, which require that a number of ports be forwarded from my external connection to the particular computer on which I happen to be working. It turns out there's a protocol for this, called [UPnP][1]. From Wikipedia:

> Universal Plug and Play (UPnP) is a set of networking protocols
> promulgated by the UPnP Forum. The goals of UPnP are to allow
> devices to connect seamlessly and to simplify the implementation of
> networks in the home (data sharing, communications, and
> entertainment) and in corporate environments for simplified
> installation of computer components.

The practical use of UPnP, from my perspective, is that it allows a device or application _inside_ the network to request specific ports to be forwarded on the gateway. This means that what used to be a manual process -- adding the necessary forwarding rules to my iptables configuration -- is now performed automatically, and only when necessary.

The [Linux UPnP Internet Gateway Device][2] project implements a Linux UPnP service. You can download the source from the project web page.

Using the gateway service is really simple:

1. Start upnpd:

        # /etc/init.d/upnpd
  
1. Start your application. You will see messages like the following in syslog (if you are logging DEBUG level messages):
  
        Aug  6 20:10:12 arcadia upnpd[19816]: Failure in
          GateDeviceDeletePortMapping: DeletePortMap: Proto:UDP Port:57875
        Aug  6 20:10:12 arcadia upnpd[19816]: AddPortMap: DevUDN:
          uuid:75802409-bccb-40e7-8e6c-fa095ecce13e ServiceID: urn:upnp-org:serviceId:WANIPConn1
         RemoteHost: (null) Prot: UDP ExtPort: 57875 Int: 192.168.1.118.57875
        Aug  6 20:10:12 arcadia upnpd[19816]: Failure in
          GateDeviceDeletePortMapping: DeletePortMap: Proto:UDP Port:11657
        Aug  6 20:10:12 arcadia upnpd[19816]: AddPortMap: DevUDN:
          uuid:75802409-bccb-40e7-8e6c-fa095ecce13e ServiceID: urn:upnp-org:serviceId:WANIPConn1
          RemoteHost: (null) Prot: UDP ExtPort: 11657 Int: 192.168.1.118.11657
      
    For each forwarding requested by the client, upnpd first attempts to remove the mapping and then creates a new rule. Exactly how upnp implements these rules on your system is controlled by `/etc/upnpd.conf` -- if you want to use something other than _iptables_, or use custom chains, this is where you would make your changes.

1. Look at your firewall rules. Upnpd modifies the _FORWARD_ chain in the _filter_ table and the _PREROUTING_ chain in the _nat_ table. You can change this behavior by editing `/etc/upnpd.conf`.

    To see forwarding rules:
  
        # iptables -nL FORWARD

     The rules might look something like this:
      
        Chain FORWARD (policy DROP)
        target     prot opt source               destination
        ACCEPT     udp  --  0.0.0.0/0            192.168.1.118       udp dpt:57875
        ACCEPT     udp  --  0.0.0.0/0            192.168.1.118       udp dpt:11657

     To see prerouting rules:

        # iptables -t nat -vnL PREROUTING

     The rules might look something like this:
  
        Chain PREROUTING (policy ACCEPT)
        target     prot opt source               destination
        DNAT       udp  --  0.0.0.0/0            0.0.0.0/0           udp dpt:11657 to:192.168.1.118:11657
        DNAT       udp  --  0.0.0.0/0            0.0.0.0/0           udp dpt:57875 to:192.168.1.118:57875

1. Upnpd will delete the mappings when they expire. The expiration time may be set by the client, or, if the client specifies no expiration, than by the "duration" configuration item in /etc/upnpd.conf.

# Configuration file

The upnpd configuration file (`/etc/upnpd.conf`) allows you to change various aspects of upnpd's behavior. Of particular interest:

- `insert_forward_rules`  
  Default: `yes`

    Whether or not upnpd needs to create entries in the `FORWARD` chain of the `filter` table. If your `FORWARD` chain has a policy of `DROP` you need set to yes.

- `forward_chain_name`  
  Default: `FORWARD`

    Normally, upnpd creates entries in the `FORWARD` chain. If you have a more advanced firewall setup this may not be the appropriate place to make changes. If you enter a custom name here, you will need to create the corresponding chain:
  
        iptables -N my-forward-chain

    You will also need to call this chain from the _FORWARD_ chain:

        iptables -A FORWARD -j my-forward-chain

- `prerouting_chain_name`  
  Default: `PREROUTING`

    Like `forward`chain`name`, but for entries in the `nat` table.

# Security considerations

Consider the following, from the [Linux IGD documentation][4]:

> UPnP version 1.0, on which this program is based, is inherently flawed...what appears to have happened is that in Microsoft's first UPnP implementation they weren't concerned with security .... Simply all they wanted was connectivity.... The UPnP server, by itself, does no security checking. If it recieves a UPnP request to add a portmapping for some ip address inside the firewall, it just does it. This program will attempt to verify the source ip contained in the UPnP request against the source ip of the actual packet, but as always, these can be forged. The UPnP server makes no attempt to verify this connection with the caller, and therefore it just assumes that whoever asked is the person really wanting it.

In other words, in the battle between security and convenience, UPnP is weighs in heavily on the convenience side. You will have to decide whether this meets your particular requirements.

[1]: http://en.wikipedia.org/wiki/Universal_Plug_and_Play
[2]: http://linux-igd.sourceforge.net/
[3]: http://drop.io/oddbitdotcom_linuxigd
[4]: http://linux-igd.sourceforge.net/documentation.php

