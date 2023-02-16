---
categories: [tech]
aliases: ["/2012/12/15/get-vm-ip/"]
title: Getting the IP address of a libvirt domain
date: "2012-12-15"
---

If you are starting virtual machines via `libvirt`, and you have
attached them to the `default` network, there is a very simple method
you can use to determine the address assigned to your running
instance:

- Libvirt runs `dnsmasq` for the `default` network, and saves leases
  in a local file (`/var/lib/libvirt/dnsmasq/default.leases` under
  RHEL).
- You can get the MAC address assigned to a virtual machine by
  querying the domain XML description.

Putting this together gets us something along the lines of:

    #!/bin/sh

    # Get the MAC address of the first interface.
    mac=$(virsh dumpxml $1 |
      xml2  |
      awk -F= '$1 == "/domain/devices/interface/mac/@address" {print $2; exit}')

    # Get the ip address assigned to this MAC from dnsmasq
    ip=$(awk -vmac=$mac '$2 == mac {print $3}' /var/lib/libvirt/dnsmasq/default.leases )
    echo $ip

([gist](https://gist.github.com/4300055))

This uses [xml2][] to transform the XML description into something
more amendable to processing in a shell script.  You could accomplish
much the same thing using some sort of XPath based tool.  For example:

    mac=$(virsh dumpxml $1 |
      xmllint --xpath //interface'[1]/mac/@address' - |
      sed 's/.*="\([^"]*\)"/\1/'
      )

`xmllint` is part of [libxml2][].

[xml2]: http://ofb.net/~egnor/xml2/
[libxml2]: http://www.xmlsoft.org/

