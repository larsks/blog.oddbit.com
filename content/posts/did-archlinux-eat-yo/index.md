---
categories: [tech]
aliases: ["/2013/04/08/did-archlinux-eat-yo/"]
title: Did Arch Linux eat your KVM?
date: "2013-04-08"
tags:
  - archlinux
  - virtualization
  - kvm
---

A recent update to [Arch Linux][] replaced the `qemu-kvm` package with
an updated version of `qemu`.  A side effect of this change is that
the `qemu-kvm` binary is no longer available, and any `libvirt` guests
on your system utilizing that binary will no longer operate.  As is
typical with Arch, there is no announcement about this incompatible
change, and queries to `#archlinux` will be met with the knowledge,
grace and decorum you would expect of that channel:

    2013-04-08T18:00 < gtmanfred> USE --enable-kvm for fucks sake
    2013-04-08T18:00 < gtmanfred> DO I HAVE TO SAY IT AGAIN?

The emulator binary is hardcoded into your domain in the `<emulator>`
emulator, and typically looks something like this:

    <emulator>/usr/bin/qemu-kvm</emulator>
 
In order to get your guests working again after the upgrade you'll
need to replace this path with an appropriate selection from one of
the other binaries provided by the `qemu` package, which include
`qemu-system-i386` and `qemu-system-x86_64`.  You'll want to select
the one appropriate for your *guest* architecture.  You can do this
manually running `virsh edit` for each affected guest, but if you have
more than a couple that rapidly becomes annoying.

We can use [XSLT][] to write a transformation that will set the
`<emulator>` to an appropriate value, and we can set things up to run
this automatically across all of our guests.  The following stylesheet
will replace the `<emulator>` tag with a path to an appropriate `qemu` (by 
extracting the `arch` attribute of the `domain/os/type` element:

    <?xml version="1.0"?>
    <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

      <!-- copy all elements verbatim... -->
      <xsl:template match="@*|node()">
        <xsl:copy>
          <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
      </xsl:template>

      <!-- ...except for the 'emulator' element. -->
      <xsl:template match="emulator">
        <emulator>/usr/bin/qemu-system-<xsl:value-of select="/*/os/type/@arch"/></emulator>
      </xsl:template>

    </xsl:stylesheet>

We're going to apply this to all of our (inactive) guests via the
`virsh edit` subcommand.  This command runs an editor (selected based
on your `VISUAL` or `EDITOR` environment variables) on your domain
XML.  We need to create an "editor" that will apply the above
transformation to its input file.  Something like this will work:

    #!/bin/sh

    tmpfile=$(mktemp "$1.patched.XXXXXX")
    xsltproc -o "$tmpfile" patch-emulator.xsl "$1"
    mv "$tmpfile" "$1"

Assuming the above script has been saved as "patch-emulator.sh" (and
made executable), we can run this across all of our inactive guests
like this:

    #!/bin/sh

    VISUAL=./patch-emulator.sh
    export VISUAL

    virsh list --inactive --name | while read vm; do
            [ "$vm" ] || continue
            virsh edit $vm
    done

[arch linux]: https://www.archlinux.org/
[xslt]: https://en.wikipedia.org/wiki/XSLT

