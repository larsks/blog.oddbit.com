---
categories: [tech]
aliases: ["/2012/09/10/awk-parsing-xml/"]
title: Parsing XML with Awk
date: "2012-09-10"
tags:
  - awk
  - xml
---

Recently, changes from the [xmlgawk][] project have been integrated into
[GNU awk][], and xmlgawk has been renamed to [gawkextlib][]. With both a
recent (post-4.0.70) gawk and gawkextlib built and installed
correctly, you can write simple XML parsing scripts using gawk.

[xmlgawk]: http://gawkextlib.sourceforge.net/
[gawkextlib]: http://gawkextlib.sourceforge.net/
[gnu awk]: https://www.gnu.org/software/gawk/

For example, let's say you would like to generate a list of disk image
files associated with a KVM virtual instance. You can use the `virsh
dumpxml` command to get output like the following:

    <devices>
      <emulator>/usr/bin/qemu-kvm</emulator>
      <disk type='file' device='disk'>
        <driver name='qemu' type='qcow2'/>
        <source file='/var/lib/libvirt/images/client.qcow2'/>
        <target dev='sda' bus='ide'/>
        <alias name='ide0-0-0'/>
        <address type='drive' controller='0' bus='0' unit='0'/>
      </disk>
     ...
    </devices>

You could then write code similar to [the
following](https://gist.github.com/4012705) to extract the relevant
information:

    @load "xml"

    XMLSTARTELEM == "disk"  {
            in_disk=1
            disk_file=""
            disk_target=""
    }

    in_disk == 1 && XMLSTARTELEM == "source" {
            disk_file=XMLATTR["file"]
    }

    in_disk == 1 && XMLSTARTELEM == "target" {
            disk_target=XMLATTR["dev"]
    }

    XMLENDELEM == "disk"    {
            in_disk=0
            print disk_target, disk_file
    }

Given the sample input above, the script will produce the following
output:

    sda /var/lib/libvirt/images/client.qcow2

The xml extension for gawk populates a number of variables that
can be used in your scripts:

- `XMLSTARTELEM` marks the start of a new element (and is set to the
  name of that element).
- `XMLATTR` is available when `XMLSTARTELEM` is set and contains the
  element attributes.
- `XMLENDELEM` marks the end of an element (and is set to the name of
  the element).

There are other variables available, but with this basic set is
becomes easy to extract information from XML documents.

