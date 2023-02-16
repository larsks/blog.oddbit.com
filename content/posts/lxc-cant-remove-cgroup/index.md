---
categories: [tech]
aliases: ["/2013/01/28/lxc-cant-remove-cgroup/"]
title: Cleaning up LXC cgroups
date: "2013-01-28"
---

I spent some time today looking at systemd (44) under Fedora (17).
When stopping an LXC container using `lxc-stop`, I would always
encounter this problem:

    # lxc-stop -n node0
    lxc-start: Device or resource busy - failed to remove cgroup '/sys/fs/cgroup/systemd/node0

This prevents one from starting a new container with the same name:

    # lxc-start -n node0 
    lxc-start: Device or resource busy - failed to remove previous cgroup '/sys/fs/cgroup/systemd/node0'
    lxc-start: failed to spawn 'node0'
    lxc-start: Device or resource busy - failed to remove cgroup '/sys/fs/cgroup/systemd/node0'

You can correct the problem manually by removing all the child cgroups
underneath `/sys/fs/cgroup/systemd/<container>`, like this:

    # find /sys/fs/cgroup/systemd/node0/ -type d |
      tac |
      xargs rmdir

The call to `tac` (which will output lines in reverse order) is
necessary because we need to start with the "deepest" directory and
work our way back up. 

This appears to be a version-specific problem.  I do not see the same
behavior with `systemd` 197 under Arch.

