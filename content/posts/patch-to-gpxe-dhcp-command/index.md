---
categories: [tech]
aliases: ["/2010/07/22/patch-to-gpxe-dhcp-command/"]
title: Patch to gPXE dhcp command
date: "2010-07-22"
tags:
  - gpxe
  - linux
  - dhcp
---

**Update**: This patch has been [accepted][1] into gPXE.

I just released a [patch][2] to [gPXE][3] that modifies the dhcp command so that it can iterate over multiple interfaces. The stock dhcp command only accepts a single interface as an argument, which can be a problem if you are trying to boot on a machine with multiple interfaces. The builtin autoboot commands attempts to resolve this, but is only useful if you expect to receive appropriate boot parameters from your dhcp server.

My patch extends the dhcp command in the following ways:

  1. It allows the "dhcp" command to accept a list of interfaces and to try them in order until it succeeds, e.g.:
    
    
    gPXE> dhcp net0 net1 net2
    

In order to preserve the original syntax of the command, this will fail on an unknown interface name:
    
    
    gPXE> dhcp foo net0
    No such interface: foo
    gPXE>
    

The "-c" flag allows it to continue:
    
    
    gPXE> dhcp -c foo net0
    No such interface: foo
    DHCP (net0 xx:xx:xx:xx:xx:xx).... ok
    gPXE>
    

  2. If given the single parameter "any" as an interface name, iterate over all known interfaces in a manner similar to autoboot():
    
    
    gPXE> dhcp any
    DHCP (net0 xx:xx:xx:xx:xx:xx)........ Connection timed out (...)
    Could not configure net0: Connection timed out (...)
    DHCP (net1 xx:xx:xx:xx:xx:xx).... ok
    gPXE>
    

I think this manages to preserve the syntax of the existing "dhcp" command while making the magic of autoboot available to gpxe scripts.

[1]: http://git.etherboot.org/?p=gpxe.git;a=commit;h=fa91c2c3269554df855107a24afec9a1149fee8f
[2]: http://gist.github.com/486907
[3]: http://etherboot.org/wiki/index.php

