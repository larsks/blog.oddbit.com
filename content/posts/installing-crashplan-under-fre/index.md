---
aliases:
- /2011/05/22/installing-crashplan-under-freebsd-8/
- /post/2011-05-22-installing-crashplan-under-freebsd-8
categories:
- tech
date: '2011-05-22'
tags:
- backup
- storage
- java
- freebsd
- crashplan
title: Installing CrashPlan under FreeBSD 8
---

This articles describes how I got [CrashPlan][1] running on my FreeBSD 8(-STABLE) system. [These instructions][2] by Kim Scarborough were my starting point, but as these were for FreeBSD 7 there were some additional steps necessary to get things working.

# Install Java

I had originally thought that it might be possible to run the CrashPlan client "natively" under FreeBSD. CrashPlan is a Java application, so this seemed like a possible solution. Unfortunately, Java under FreeBSD 8 seems to be a lost cause. I finally gave up and just installed Java under Linux.

## Set up your Linux compatability environment

The simplest way to do this is to follow the instructions in the [FreeBSD Handbook][3]. This will get you a Fedora 10 based Linux userspace, which should be more than sufficient. I'm using a CentOS 5.6 userspace, but for what we're doing it shouldn't matter, modulo some minor differences in paths.

Note that Linux software running in this environment will have a modified view of your filesystem. In particular, /etc will map to /compat/linux/etc, and ZFS filesystems with non-default mountpoints seem to behave oddly (they are accessible, but not necessarily visible before you access them). This may require some workarounds in CrashPlan, depending on what you're trying to back up.

## Install Java JRE

I installed a compatible Java environment from the CentOS package repository:
    
    
    # chroot /compat/linux bash
    bash-3.2# yum install java-1.6.0-openjdk
    bash-3.2# exit
    

# Install CrashPlan

## Install the CrashPlan software

  - Download [CrashPlan for Linux][4]

  - Unpack the archive (named something like CrashPlan_3.0.3_Linux.tgz)

  - Change to the CrashPlan-install directory.

  - Run the following commands:
    
    
    # export PATH=/compat/linux/usr/lib/jvm/jre-1.6.0-openjdk/bin:$PATH
    # /compat/linux/bin/bash install.sh
    

  - Install CrashPlan into /usr/local. When prompted for where to locate init scripts ("What directory contains your SYSV init scripts?" and "What directory contains your runlevel init links?"), enter /tmp (because the installed init scripts aren't ideal for your FreeBSD environment -- we'll install our own later on).

## Fix Java

The Linux runtime provided by the FreeBSD Linux compatability layer does not include all of the features of recent Linux kernels. In particular, it is missing the epoll* syscalls, which will cause Java to die with a _Function not implemented_ error. The workaround for this is documented in the [linux-kernel][5] page on the [FreeBSD wiki][6]:

> If you run an application in the linux java which wants to use the linux epoll functions (you should see "not implemented" messages in dmesg), you can start java with the argument -Djava.nio.channels.spi.SelectorProvider=sun.nio.ch.PollSelectorProvider

## Install an rc script

Place the following script into /usr/local/etc/rc.d/crashplan:
    
    
    #!/bin/sh
    #
    
    # PROVIDE: crashplan
    # REQUIRE: NETWORKING
    # KEYWORD: shutdown
    
    . /etc/rc.subr
    
    name="crashplan"
    rcvar=`set_rcvar`
    start_cmd=crashplan_start
    stop_cmd=crashplan_stop
    
    crashplan_start () {
      /compat/linux/bin/bash /usr/local/crashplan/bin/CrashPlanEngine start
    }
    
    crashplan_stop () {
      /compat/linux/bin/bash /usr/local/crashplan/bin/CrashPlanEngine stop
    }
    
    load_rc_config $name
    run_rc_command "$1"
    

And then add:
    
    
    crashplan_enable="YES"
    

To /etc/rc.conf (or /etc/rc.conf.local).

## Start CrashPlan

Run:
    
    
    /usr/local/etc/rc.d/crashplan start
    

Wait a moment, then run:
    
    
    /compat/linux/bin/bash /usr/local/crashplan/bin/CrashPlanEngine status
    

This should verify that CrashPlan is running.

# Connect CrashPlan client

Follow the instructions provided by CrashPlan for [connecting to a headless CrashPlan desktop][7].

[1]: http://crashplan.com/
[2]: http://kim.scarborough.chicago.il.us/do/nerd/tips/crashplan
[3]: http://www.freebsd.org/doc/handbook/linuxemu-lbc-install.html
[4]: http://www.crashplan.com/consumer/download.html?os=Linux
[5]: http://wiki.freebsd.org/linux-kernel
[6]: http://wiki.freebsd.org/
[7]: http://stgsupport.crashplan.com/doku.php/how_to/configure_a_headless_client