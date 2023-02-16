---
categories: [tech]
aliases: ["/2012/12/21/parsing-libvirt-xml/"]
title: Parsing Libvirt XML with xmllint
date: "2012-12-21"
---

I've been playing around with the [LXC][] support in libvirt recently,
and I'm trying to use a model where each LXC instance is backed by a
dedicated LVM volume.  This means that the process of starting an
instance is:

- mount the instance root filesystem if necessary
- start the instance

It's annoying to have to do this by hand.  I could simply add all the
LXC filesystems to `/etc/fstab`, but this would mean and extra step
when creating and deleting each instance.

I thought about creating a wrapper script to handle the mounting (and
unmounting, perhaps) for me, but this leads to another problem: I need
a way to figure out which backing device corresponding to the virtual
instance I'm trying to boot.

I could just adopt a strict naming scheme, so that for a given
instance "foo" the backing store would be
`/dev/vg_something/domain-foo`, but that's too easy!  In order to make
life interesting:

- I've added some namespace-prefixed metadata to the instance XML
  description, and 
- Written a shell script to extract this data (and more) using
  `xmllint`.

## Metadata

The Libvirt domain XML format allows for a general [metadata
section][metadata]:

> The `metadata` node can be used by applications to store custom
> metadata in the form of XML nodes/trees. Applications **must** use
> custom namespaces on their XML nodes/trees, with only one top-level
> element per namespace (if the application needs structure, they
> should have sub-elements to their namespace element). 

This means that if you want to add metadata to a domain description,
you need to define a namespace and use a namespace prefix. For
example, if I want to add a `device` element pointing at the backend
storage device for my domain, it might look like this:

    <metadata xmlns:ob="http://oddbit.com/ns/libvirt/1">
        <ob:device>/dev/vg0/instance</ob:device>
    </metadata>

## Extracting metadata with xmllint

The `xmllint` tool, part of [libxml][], can extract nodes from an XML
document using [xpath][] expressions.  Unfortunately, while `xmllint`
does have namespace support, it's not particularly convenient.  Using
the `--shell` mode there's a helpful `setns` command:

    $ xmllint --shell domain.xml
    / > setns x=http://oddbit.com/ns/libvirt/1
    / > xpath //x:device
    Object is a Node Set :
    Set contains 1 nodes:
    1  ELEMENT ob:device

But that's not available from the command line.  We can use the
`namespace-uri()` and `local-name()` xpath functions to get to the
same place, albeit more verbosely.  An equivalent to the above shell
session would be:

    $ xmllint --xpath '//*[namespace-uri()="http://oddbit.com/ns/libvirt/1" and local-name()="device"]'
    <ob:device>/dev/vg0/instance</ob:device>

## Putting it all together

The following shell script looks through all inactive LXC domains and
figures out:

- If it should try to start them, using the `<oddbit:autostart>` element,
- What the backend storage is, using the `<oddbit:device>` element,
  and
- Where to mount it, by looking for the libvirt `<filesystem>` element
  with a target of `/`.

      #!/bin/sh

      tmpfile=$(mktemp)
      trap 'rm -f $tmpfile' EXIT

      virsh -c lxc:/// list --name --inactive | while read domain; do
        [ "$domain" ] || continue

        virsh dumpxml $domain > $tmpfile

        autostart=$(xmllint --xpath '//domain/metadata/*[namespace-uri()="http://oddbit.com/ns/libvirt/1" and local-name()="autostart"]/text()' $tmpfile)

        [ "$autostart" = True ] || continue

        device=$(xmllint --xpath '//domain/metadata/*[namespace-uri()="http://oddbit.com/ns/libvirt/1" and local-name()="device"]/text()' $tmpfile)
        mount=$(xmllint --xpath 'string(//filesystem/target[@dir = "/"]/../source/@dir)' $tmpfile)

        echo "$domain $autostart $device $mount"
      done

I'm not actually planning on using this in practice.  I'll
probably go the naming scheme route.  But this was fun to figure out.

[lxc]: http://lxc.sourceforge.net/
[metadata]: http://libvirt.org/formatdomain.html#elementsMetadata
[libxml]: http://www.xmlsoft.org/
[xpath]: https://en.wikipedia.org/wiki/XPath

