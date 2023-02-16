---
aliases:
- /2016/02/07/systemd-nspawn-for-fun-and-well-mostly-f/
- /post/2016-02-07-systemd-nspawn-for-fun-and-well-mostly-f
categories:
- tech
date: '2016-02-07'
tags:
- systemd
- containers
- qemu
- raspberrypi
title: Systemd-nspawn for fun and...well, mostly for fun
---

`systemd-nspawn` has been called ["chroot on steroids"][archquote],
but if you think of it as [Docker][] with a slightly different target
you wouldn't be far wrong, either.  It can be used to spawn containers
on your host, and has a variety of options for configuring the
containerized environment through the use of private networking, bind
mounts, capability controls, and a variety of other facilities that
give you flexible container management.

[archquote]: https://wiki.archlinux.org/index.php/Systemd-nspawn

There are many different ways in which it can be used.  I'm going to
focus on one that's a bit of a corner use case that I find
particularly interesting.  In this article we're going to explore how
we can use [systemd-nspawn][] to spawn lightweight containers for
architectures other than that of our host system.

## Why systemd-nspawn?

While everything described in this article could be accomplished
through the use of `chroot` and a chunk of additional configuration,
using `systemd-nspawn` makes it much easier.  For example,
`systemd-nspawn` takes care of making virtual filesystems like
`/proc`, `/sys`, and a minimal `/dev` available inside the container
(without which some programs simply won't work).  And of course
`systemd-nspawn` takes care of cleaning up these mounts when the
container exits.  For a simple container, this:

    # systemd-nspawn -D /mnt /some/command

Is roughly equivalent to:

    # mount -o bind /proc /mnt/proc
    # mount -o bind /sys /mnt/sys
    # mount -t tmpfs tmpfs /mnt/run
    # mount -t tmpfs tmpfs /mnt/dev
    # ...populate /mnt/dev here...
    # chroot /mnt /some/command
    # umount /mnt/dev
    # umount /mnt/run
    # umount /mnt/sys
    # umount /mnt/proc

`systemd-nspawn` does all of this for us, and does much of it via
private mount namespaces so that the temporary filesystems aren't
visible from the host.

## In which we perform magic

Linux allows you to run binaries intended for other architectures
via the [binfmt-misc][] subsystem, which allows you to use bits at the
beginning of a file to match against an appropriate interpreter.  This
can be used, for example, to make Java binaries directly executable.
We're going to use this technique to accomplish the following:

- Teach our system how to run Raspberry Pi ARM binaries, and
- Allow us to spawn a `systemd-nspawn` container into a Raspberry Pi
  filesystem.

When a `systemd`-based system boots, the [systemd-binfmt][] service
(if it's enabled) will automatically register configurations found in
`/etc/binfmt.d` or `/usr/lib/binfmt.d`.  You can set these up by hand,
of course, but we're going to take the easy route and install the
`qemu-user-static` package, which includes both the necessary `binfmt.d`
configuration files as well as the associated emulators:

    # dnf -y install qemu-user-static

The `qemu-user-static` package on my system has installed, among other files,
`/usr/lib/binfmt.d/qemu-arm.conf`, which looks like this:

    :qemu-arm:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-arm-static:

This gets registered with `/proc/sys/fs/binfmt_misc/register` and
informs the kernel that there is a new binfmt called `qemu-arm`, and
that files that contain the specified byte pattern in the header
should be handled with `/usr/bin/qemu-arm-static`.

With all this set up, we can mount a Raspberry Pi filesystem (I'm
starting with [minibian][])...

    # tar xf 2015-11-12-jessie-minibian.tar.gz
    # losetup -fP --show 2015-11-12-jessie-minibian.img
    /dev/loop1
    # mount /dev/loop1p2 /mnt
    # mount /dev/loop1p1 /mnt/boot

...and then start up a process in it:

    # systemd-nspawn -D /mnt
    Spawning container mnt on /mnt.
    Press ^] three times within 1s to kill container.
    root@mnt:~#

And there we are!  We're now running a shell inside a container
running an ARM userspace.  We can modify the image by installing or
udpating packages or making any other necessary configuration changes:

    root@mnt:/# apt-get install raspberrypi-bootloader
    Reading package lists... Done
    Building dependency tree       
    Reading state information... Done
    The following extra packages will be installed:
      libraspberrypi-bin libraspberrypi0
    The following packages will be upgraded:
      libraspberrypi-bin libraspberrypi0 raspberrypi-bootloader
    3 upgraded, 0 newly installed, 0 to remove and 34 not upgraded.
    Need to get 32.5 MB of archives.
    After this operation, 827 kB of additional disk space will be used.
    Do you want to continue? [Y/n] 

When we're done, we exit our container:

    root#mnt:/# exit

Unmount the directory:o

    # umount /mnt

And finally clean up the loopback device:

    # losetup -d /dev/loop1

Now we have an updated image file that we can write to an SD card and
use to boot our Raspberry Pi.

**NB** You'll note that in this document I'm mounting `loop1p2` on `/`
and `loop1p1` on `/boot`.  You obviously don't need `/boot` in your
container in order for things to run, but you will regret not mounting
it if you happen to install an updated kernel package, which needs to
populate `/boot` with the new kernel image.

## Bonus: growing the image

The stock [minibian][] image doesn't have much free space on it; this
is intentional, and in general you're expected to grow the root
partition and resize the filesystem after booting on your Pi.
However, if we're going to use the above process to pre-configure our
image, there's a good chance we'll need more space immediately.  We
start by growing the size of the image file itself; you can that with
`qemu-img`, like this:

    # qemu-img resize 2015-11-12-jessie-minibian.img 2G

Or by using `truncate`:

    # truncate -s 2G 2015-11-12-jessie-minibian.img

Or by using `dd`:

    # dd of=2015-11-12-jessie-minibian.img if=/dev/zero \
      count=0 bs=1G seek=2

Once the file has been extended, we need to grow the corresponding
partition.  Assuming that you have a recent version of `util-linux`
(where "recent" means "at least [v2.26.2][]) installed, this is easy:

[v2.26.2]: http://karelzak.blogspot.com/2015/05/resize-by-sfdisk.html

    # echo ", +" | sfdisk -N 2 2015-11-12-jessie-minibian.img

And lastly, we need to grow the filesystem.  This requires
attaching the image to a loop device:

    # losetup -fP --show 2015-11-12-jessie-minibian.img
    /dev/loop1

And then:

    # e2fsck -f /dev/loop1p2
    # resize2fs /dev/loop1p2

Now when we mount the filesystem:

    # mount /dev/loop1p2 /mnt
    # mount /dev/loop1p1 /mnt/boot

We see that there is more space available:

    # df -h /mnt
    Filesystem      Size  Used Avail Use% Mounted on
    /dev/loop1p2    1.9G  432M  1.4G  24% /mnt

## Bonus: Static qemu-arm binaries

Earlier we saw that it was necessary to mount `/lib64` into my
Raspberry Pi container because the `qemu-arm` binary was dynamically
linked.  You can acquire statically built versions of the QEMU
binaries from the Debian project, e.g., [here][qemu-static]:

- https://packages.debian.org/sid/amd64/qemu-user-static/download

Then unpack the `.deb` file and extract the `qemu-arm-static` binary:

    $ ar xv qemu-user-static_2.5+dfsg-5_amd64.deb
    x - debian-binary
    x - control.tar.gz
    x - data.tar.xz
    $ tar xf data.tar.xz ./usr/bin/qemu-arm-static

And copy it into place:

    # cp qemu-arm-static /usr/bin/qemu-arm

And now our earlier command will work without further modification:

    # systemd-nspawn -q --bind /usr/bin/qemu-arm -D /mnt /bin/bash
    root@mnt:/#

[binfmt-misc]: https://www.kernel.org/doc/Documentation/binfmt_misc.txt
[minibian]: https://minibianpi.wordpress.com/
[qemu-static]: https://packages.debian.org/sid/amd64/qemu-user-static/download
[systemd-binfmt]: https://www.freedesktop.org/software/systemd/man/binfmt.d.html
[systemd-nspawn]: https://www.freedesktop.org/software/systemd/man/systemd-nspawn.html
[docker]: http://docker.com