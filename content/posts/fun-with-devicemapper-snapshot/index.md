---
aliases:
- /2018/01/25/fun-with-devicemapper-snapshots/
- /post/2018-01-25-fun-with-devicemapper-snapshots
categories:
- tech
date: '2018-01-25'
tags:
- storage
- devicemapper
title: Fun with devicemapper snapshots
---

I find myself working with [Raspbian][] disk images fairly often. A
typical workflow is:

[raspbian]: https://www.raspberrypi.org/downloads/raspbian/

- Download the disk image.
- Mount the filesystem somewhere to check something.
- Make some changes or install packages just to check something else.
- Crap I've made changes.

...at which point I need to fetch a new copy of the image next time I
want to start fresh.

Sure, I could just make a copy of the image and work from there, but
what fun is that? This seemed like a perfect opportunity to learn more
about the [device mapper][] and in particular how the [snapshot][]
target works.

[device mapper]: https://www.kernel.org/doc/Documentation/device-mapper/
[snapshot]: https://www.kernel.org/doc/Documentation/device-mapper/snapshot.txt

## Making sure we have a block device

The device mapper only operates on block devices, so the first thing
we need to do is to make the source image available as a block device.
We can do that with the [losetup][] command, which maps a file to a
virtual block device (or *loop* device).

[losetup]: http://manpages.ubuntu.com/manpages/xenial/man8/losetup.8.html

I run something like this:

    losetup --find --show --read-only 2017-11-29-raspbian-stretch-lite.img

This will find the first available block device, and then use it make
my disk image available in read-only mode. Those of you who are
familiar with `losetup` may be thinking, "you know, `losetup` knows
how to handle partitioned devices", but I am ignoring that for the
purpose of using device mapper to solve things.

## Mapping a partition

We've just mapped the entire disk image to a block device. We can't
use this directly because the image has multiple partitions:

    # sfdisk -l /dev/loop0
    Disk /dev/loop0: 1.7 GiB, 1858076672 bytes, 3629056 sectors
    Units: sectors of 1 * 512 = 512 bytes
    Sector size (logical/physical): 512 bytes / 512 bytes
    I/O size (minimum/optimal): 512 bytes / 512 bytes
    Disklabel type: dos
    Disk identifier: 0x37665771

    Device       Boot Start     End Sectors  Size Id Type
    /dev/loop0p1       8192   93236   85045 41.5M  c W95 FAT32 (LBA)
    /dev/loop0p2      94208 3629055 3534848  1.7G 83 Linux

We want  to expose partition 2, which contains the root filesystem. We
can see from the above output that partition 2 starts at sector
`94208` and extends for `3534848` sectors (where a *sector* is for our
purposes 512 bytes). If you need to get at this information
programatically, `sfdisk` has `--json` option that can be useful; for
example:

    # p_start=$(sfdisk --json /dev/loop0 |
      jq ".partitiontable.partitions[1].start")
    # echo $p_start
    94208

We want to expose this partition as a distinct block device. We're
going to do this by creating a device mapper `linear` target. To
create device mapper devices, we use the `dmsetup` command; the basic
syntax is:

    dmsetup create <name>

By default, this expects to read a table describing the device on
`stdin`, although it is also possible to specify one on the command
line. A table consists of one or more lines of the format:

    <base> <length> <target> [<options>]

Where `<base>` is the starting offset in sectors for this particular
segment, `<length>` is the length, `<target>` is the target type
(linear, snapshot, zero, etc), and the option are specific to the
particular target in use.

To create a device exposing partition 2 of our image, we run:

    # dmsetup create base <<EOF
    0 3534848 linear /dev/loop0 94208
    EOF

This creates a device named `/dev/mapper/base`. Sectors `0` through
`3534848` of this device will be provided by `/dev/loop0`, starting at
offset `94208`. At this point, we can actually mount the filesystem:

    # mount -o ro /dev/mapper/base /mnt
    # ls /mnt
    bin   dev  home  lost+found  mnt  proc  run   srv  tmp  var
    boot  etc  lib   media       opt  root  sbin  sys  usr
    # umount /mnt

But wait, there's a problem! These disk images usually have very
little free space. We're going to want to extend the length of our
base device by some amount so that we have room for new packages and
so forth. Fortunately, since our goal is that all writes are going to
a snapshot, we don't need to use *real* space. We can add another
segment to our table that uses the [zero][] target.

[zero]: https://www.kernel.org/doc/Documentation/device-mapper/zero.txt

Let's first get rid of the device we just created:

    # dmsetup remove base

And create a new one:

    # dmsetup create base <<EOF
    0 3534848 linear /dev/loop0 94208
    3534848 6950912 zero
    EOF

This extends our `base` device out to 5G (or a total of `10485760`
sectors), although attempting to read from anything beyond sector
`3534848` will return zeros, and writes will be discarded. But that's
okay, because the space available for writes is going to come from a
COW ("copy-on-write") device associated with our snapshot: in other
words, the capacity of our snapshot will be linked to size of our COW
device, rather than the size of the underlying base image.

## Creating a snapshot

Now that we've sorted out our base image it's time to create the
snapshot device. According to [the documentation][snapshot], the
table entry for a snapshot looks like:

    snapshot <origin> <COW device> <persistent?> <chunksize>

We have our `<origin>` (that's the base image we created in the
previous step), but what are we going to use as our `<COW device>`?
This is a chunk of storage that will receive any writes to the
snapshot device. This could be any block device (another loop device,
an LVM volume, a spare disk partition), but for my purposes it seemed
convenient to use a RAM disk, since I had no need for persistent
changes. We can use the [zram][] kernel module for that. Let's start
by loading the module:

[zram]: https://www.kernel.org/doc/Documentation/blockdev/zram.txt

    # modprobe zram

Without any additional parameters this will create a single RAM disk,
`/dev/zram0`. Initially, it's not very big:

    # blockdev --getsz /dev/zram0
    0

But we can change that using the `sysfs` interface provided in
`/sys/block/zram0/`. The `disksize` option controls the size of the
disk. Let's say we want to handle up to 512M of writes; that means we
need to write the value `512M` to `/sys/block/zram0/disksize`:

    echo 512M > /sys/block/zram0/disksize

And now:

    # blockdev --getsz /dev/zram0
    1048576

We now have all the requirements to create our snapshot device:

    dmsetup create snap <<EOF
    0 10485760 snapshot /dev/mapper/base /dev/zram0 N 16
    EOF

This creates a device named `/dev/mapper/snap`. It is a 5G block
device backed by `/dev/mapper/base`, with changes written to
`/dev/zram0`. We can mount it:

    # mount /dev/mapper/snap /mnt
    # df -h /mnt
    Filesystem        Size  Used Avail Use% Mounted on
    /dev/mapper/snap  1.7G  943M  623M  61% /mnt

And we can resize it:

    # resize2fs !$
    resize2fs /dev/mapper/snap
    resize2fs 1.43.3 (04-Sep-2016)
    Filesystem at /dev/mapper/snap is mounted on /mnt; on-line resizing required
    old_desc_blocks = 1, new_desc_blocks = 1
    The filesystem on /dev/mapper/snap is now 1310720 (4k) blocks long.

    # df -h /mnt
    Filesystem        Size  Used Avail Use% Mounted on
    /dev/mapper/snap  4.9G  944M  3.8G  20% /mnt

You'll note here that it looks like we have a 5G device, because
that's the size of our base image. Because we've only allocated
`512M` to our COW device, we can actually only handle up to 512M of
writes before we invalidate the snapshot.

We can inspect the amount of our COW device that has been consumed by
changes by using `dmsetup status`:

    # dmsetup status snap
    0 10485760 snapshot 107392/1048576 0

This tells us that `107392` sectors of `1048576` total have been
consumed so far (in other words, about 54M out of 512M). We can get
similar information from the perspective of the `zram` module using
`zramctl`:

    # zramctl
    NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
    /dev/zram0 lzo           512M 52.4M   34K   72K       4

This information is also available in `/sys/block/zram0/mm_stat`, but
without any labels.