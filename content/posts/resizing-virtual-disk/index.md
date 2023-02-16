---
categories: [tech]
aliases: ["/2012/10/24/resizing-virtual-disk/"]
title: Growing a filesystem on a virtual disk
date: "2012-10-24"
tags:
  - virtualization
  - kvm
  - storage
---

Occasionally we will deploy a virtual instance into our KVM
infrastructure and realize after the fact that we need more local disk
space available.  This is the process we use to expand the disk image.
This process assumes the following:

- You're using legacy disk partitions.  The process for LVM is similar
  and I will describe that in another post (it's generally identical
  except for an additional `pvresize` thrown in and `lvextend` in
  place of `resize2fs`).
- The partition you need to resize is the last partition on the disk.

This process will work with either a `qcow2` or `raw` disk image.  For
`raw` images you can also run `fdisk` on the host, potentially saving
yourself a reboot, but that's less convenient for `qcow2` format
images.

---

We start with a 5.5G root filesystem with 4.4G free:

    [root@localhost ~]# df -h /
    Filesystem      Size  Used Avail Use% Mounted on
    /dev/vda2       5.5G  864M  4.4G  17% /

We need to shut down the system to grow the underlying image:

    [root@localhost ~]# poweroff

On the host, we use the `qemu-img resize` command to grow the image.
First we need the path to the underlying disk image:

    [lars@madhatter blog]$ virsh -c qemu:///system dumpxml lars-test-0 | grep file
        <disk type='file' device='disk'>
          <source file='/var/lib/libvirt/images/lars-test-0-1.img'/>

And now we increase the image size by 10G:

    [lars@madhatter blog]$ sudo qemu-img resize /var/lib/libvirt/images/lars-test-0.img +10G
    Image resized.

Now reboot the instance:

    [lars@madhatter blog]$ virsh -c qemu:///system start lars-test-0

And login in on the console:

    [lars@madhatter blog]$ virsh -c qemu:///system console lars-test-0
    Connected to domain lars-test-0
    Escape character is ^]

    Fedora release 17 (Beefy Miracle)
    Kernel 3.6.2-4.fc17.x86_64 on an x86_64 (ttyS0)

    localhost login: root
    Password:

We're going to use `fdisk` to modify the partition layout.  Run
`fdisk` on the system disk:

    [root@localhost ~]# fdisk /dev/vda
    Welcome to fdisk (util-linux 2.21.2).

    Changes will remain in memory only, until you decide to write them.
    Be careful before using the write command.

Print out the existing partition table and verify that you really are
going to be modifying the final partition:

    Command (m for help): p

    Disk /dev/vda: 19.3 GB, 19327352832 bytes
    16 heads, 63 sectors/track, 37449 cylinders, total 37748736 sectors
    Units = sectors of 1 * 512 = 512 bytes
    Sector size (logical/physical): 512 bytes / 512 bytes
    I/O size (minimum/optimal): 512 bytes / 512 bytes
    Disk identifier: 0x00007d9f

       Device Boot      Start         End      Blocks   Id  System
    /dev/vda1   *        2048     1026047      512000   83  Linux
    /dev/vda2         1026048     5154815     2064384   82  Linux swap / Solaris
    /dev/vda3         5154816    16777215     5811200   83  Linux

Delete and recreate the final partition, in this case `/dev/vda3`...

    Command (m for help): d
    Partition number (1-4): 3
    Partition 3 is deleted

...and create a new partition, accepting all the defaults.  This will
create a new partition starting in the same place and extending to the
end of the disk:

    Command (m for help): n
    Partition type:
       p   primary (2 primary, 0 extended, 2 free)
       e   extended
    Select (default p): p
    Partition number (1-4, default 3): 3
    First sector (5154816-37748735, default 5154816): 
    Using default value 5154816
    Last sector, +sectors or +size{K,M,G} (5154816-37748735, default 37748735): 
    Using default value 37748735
    Partition 3 of type Linux and of size 15.6 GiB is set

You can print out the new partition table to see that indeed
`/dev/vda3` is now larger:

    Command (m for help): p

    Disk /dev/vda: 19.3 GB, 19327352832 bytes
    16 heads, 63 sectors/track, 37449 cylinders, total 37748736 sectors
    Units = sectors of 1 * 512 = 512 bytes
    Sector size (logical/physical): 512 bytes / 512 bytes
    I/O size (minimum/optimal): 512 bytes / 512 bytes
    Disk identifier: 0x00007d9f

       Device Boot      Start         End      Blocks   Id  System
    /dev/vda1   *        2048     1026047      512000   83  Linux
    /dev/vda2         1026048     5154815     2064384   82  Linux swap / Solaris
    /dev/vda3         5154816    37748735    16296960   83  Linux

Write the changes to disk:

    Command (m for help): w
    The partition table has been altered!

    Calling ioctl() to re-read partition table.

    WARNING: Re-reading the partition table failed with error 16: Device or resource busy.
    The kernel still uses the old table. The new table will be used at
    the next reboot or after you run partprobe(8) or kpartx(8)
    Syncing disks.

**Note the warning!**  The kernel has cached a copy of the old
partition table.  We need to reboot the system before our changes are
visible!  So we reboot the system:

    [root@localhost ~]# reboot

And log back in.  Run `df` to see the current size of the root
filesystem:
    
    [root@localhost ~]# df -h /
    Filesystem      Size  Used Avail Use% Mounted on
    /dev/vda3       5.5G  864M  4.4G  17% /

Now run `resize2fs` to resize the root filesystem so that it expands
to fill our extended `/dev/vda3`:

    [root@localhost ~]# resize2fs /dev/vda3
    resize2fs 1.42.3 (14-May-2012)
    Filesystem at /dev/vda3 is mounted on /; on-line resizing required
    old_desc_blocks = 1, new_desc_blocks = 1
    The filesystem on /dev/vda3 is now 4074240 blocks long.

Run `df` again to see that we now have additional space available:

    [root@localhost ~]# df -h /
    Filesystem      Size  Used Avail Use% Mounted on
    /dev/vda3        16G  867M   14G   6% /
    [root@localhost ~]# 

