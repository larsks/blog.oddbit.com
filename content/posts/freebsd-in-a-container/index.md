---
categories: [tech]
title: "Running FreeBSD in a Container"
date: "2023-08-17"
tags:
  - freebsd
  - podman
  - virtualization
  - qemu
  - containers
---

I was recently working on some enhancements to [Picocom] and I wanted to add support for [FreeBSD] to the GitHub workflows I'm using to test the code. GitHub doesn't provide a FreeBSD runtime environment, and I'm not interested in hosting my own GitHub runner (and GitHub [doesn't support FreeBSD runners in any case][#385]).

[picocom]: https://picocom-ng.oddbit.com
[#385]: https://github.com/actions/runner/issues/385
[freebsd]: FreeBSD

I decided to build a container image that runs FreeBSD in an emulator. I had several goals for this project:

- The build process must be fully automatic -- no manual work involved in either running the installer or configuring the FreeBSD environment.
- The repository needs to be hostable on GitHub (so no hosting a disk image in the repository)
- The solution cannot rely on any static keys. Authentication tokens need to be passed in externally or generated at runtime.

I think I've achieved these goals (and more!) with the [freebsd-container] project. At a high level, we're just running a FreeBSD virtual machine with [QEMU], but I think the details are interesting.

[freebsd-container]: https://github.com/picocom-ng/freebsd-container
[qemu]: https://www.qemu.org/

{{< toc >}}

## A manual install

Let's first look at the process of running a manual install of FreeBSD.

We'll use the [bootonly] version of the FreeBSD installer, since that's a relatively small download (just under 400MB):

[bootonly]: https://download.freebsd.org/releases/amd64/amd64/ISO-IMAGES/13.2/FreeBSD-13.2-RELEASE-amd64-bootonly.iso

```
curl -OL https://download.freebsd.org/releases/amd64/amd64/ISO-IMAGES/13.2/FreeBSD-13.2-RELEASE-amd64-bootonly.iso
```

We need to create a target volume for the install. I'm going to suggest we create a 2GB qcow2 format image using the `qemu-img` command:

```
qemu-img create -f qcow2 freebsd.img 2G
```

We can then boot the installer and target that image with the following `qemu` command line:

```
qemu-system-x86_64 -smp 1 -m 256 \
  -cdrom "FreeBSD-13.2-RELEASE-amd64-bootonly.iso" \
  -drive if=virtio,file="freebsd.img" \
  -netdev user,id=net0 \
  -device virtio-net-pci,netdev=net0
```

That will boot the installer in a graphic console window:

{{< figure src="freebsd-install-1.png" >}}

At this point you can start walking through the steps of a manual install.

## A fully automated install

We want the entire installation and configuration process to be automated -- this helps ensure a consistent result and provides a clear recipe for reproducing the same configuration. FreeBSD does support scripted installs, but if you go looking for information on the topic you'll find many older pages that references the `sysinstall` installer, which was used in FreeBSD 9 and earlier. The [man page for `sysinstall`][sysinstall] is informative:

> This utility is a prototype which lasted several years past its expiration
> date and is greatly in need of death.

[sysinstall]: https://man.freebsd.org/cgi/man.cgi?query=sysinstall&apropos=0&sektion=0&manpath=FreeBSD+9.3-RELEASE&arch=default&format=html#BUGS

Sysinstall was replaced by [`bsdinstall`][bsdinstall] in FreeBSD 10 (released in 2014, which tells you something about how long the Internet holds onto useless information). Bsdinstall does support scripted installs, and the process is described in the [`SCRIPTING` section of the `bsdinstall` man page][scripting]:

[bsdinstall]: https://wiki.freebsd.org/BSDInstall
[scripting]: https://man.freebsd.org/cgi/man.cgi?bsdinstall(8)#SCRIPTING

> On FreeBSD release media, such a script placed at /etc/installerconfig
will be run at boot time and the system will be rebooted automatically
after the installation has completed.

The `installerconfig` script consists of two parts:

1. A preamble used to provide configuration to the installer, and
2. A post-install configuration script that is run to configure the target system after the installer completes.

The two parts are separated by the `#!/bin/sh` line of the postinstall script. A simple `installerconfig` file might look like this:

```
export PARTITIONS=DEFAULT
export DISTRIBUTIONS="kernel.txz base.txz"
export HOSTNAME=freebsd
export BSDINSTALL_DISTSITE="https://download.freebsd.org/releases/amd64/13.2-RELEASE"
export INTERFACES=vtnet0

export nonInteractive="YES"

# Acquire an address using DHCP.
dhclient $INTERFACES

#!/bin/sh

sysrc ifconfig_DEFAULT=DHCP
sysrc sshd_enable=YES
sysrc growfs_enable=YES
```

Note that using `PARTITIONS=DEFAULT` in the `installerconfig` script gets us an MBR-style partition layout:

```
root# gpart show
=>     63  4194241  vtbd0  MBR  (2.0G)
       63        1         - free -  (512B)
       64  4194240      1  freebsd  [active]  (2.0G)

=>      0  4194240  vtbd0s1  BSD  (2.0G)
        0  3983360        1  freebsd-ufs  (1.9G)
  3983360   208896        2  freebsd-swap  (102M)
  4192256     1984           - free -  (992K)
```

We'll change that configuration later, but it's fine for what we're doing right now.

In order to make use of that script, we need to produce a patched version of the FreeBSD install image with the script installed int he appropriate location. We can do that by:

1. Extracting the files from the ISO image into a local directory
2. Placing our `installerconfig` script in `/etc`
3. Generating a new ISO image

There several ways of accomplishing the first step; for now we'll simply mount the ISO on `/mnt` and copy out the files (note that the following steps need to be run as `root` in order to preserve file permissions and ownership):

```
mount -o loop,ro FreeBSD-13.2-RELEASE-amd64-bootonly.iso /mnt
mkdir workdir
rsync -a /mnt/ workdir/
umount /mnt
```

Then we copy in our `installerconfig` file:

```
cp installerconfig workdir/etc/installerconfig
```

We will also need to update `/etc/fstab` in the image, which is looking for a volume labelled explicitly `13_2_RELEASE_AMD64_BO`. We *could* just give our new ISO image the same label, but I find it easiest to update the `fstab` file:

```
cat > workdir/etc/fstab <<EOF
/dev/iso9660/FREEBSD_INSTALL / cd9660 ro 0 0
EOF
```

Finally, we produce an updated ISO image:

```
mkisofs -D -R -b boot/cdboot -allow-leading-dots -no-emul-boot \
  -o installer.iso -V FREEBSD_INSTALL workdir
```

This gives us a new installer image, `installer.iso`. If we boot that using the same command we used previously (don't forget to create the target qcow2 image first if you haven't already)...

```
qemu-system-x86_64 -smp 1 -m 256 \
  -cdrom "installer.iso" \
  -drive if=virtio,file="freebsd.img" \
  -netdev user,id=net0 \
  -device virtio-net-pci,netdev=net0
```

...it should run a fully scripted install and then reboot the virtual machine from the freshly installed image.

### Bugs! Bugs everywhere!

That was a good story, but what will *actually* happen is the install will fail with the following error:

{{< figure src=freebsd-install-error.png >}}

It turns out there is a [critical bug] in the installer that prevents it from calculating the checksums on the downloaded files. Read the bug for details; the workaround is to patch the installer. Fortunately, we're already generating a custom ISO, so we can simply replace `/usr/libexec/bsdinstall/script` with [this file]:

```
curl -o workdir/usr/libexec/bsdinstall/script ...
```

[critical bug]: https://bugs.freebsd.org/bugzilla/show_bug.cgi?id=273148
[this file]: https://raw.githubusercontent.com/picocom-ng/freebsd-container/main/installer_patches/usr/libexec/bsdinstall/script

With this patch in place, if you rerun the installer it will complete successfully:

{{< figure src="freebsd-install-complete.png" >}}

## Building the container

We've established how to run a fully scripted install with the FreeBSD installer. What do we need to do to stuff all of our work into a container image? I decided to structure the `Containerfile` as a multi-stage build, both for reasons of organization and to enforce some separation of concerns between the stages.

### Stage 1: Fetch the installer

In the first stage of the container build process, we fetch the installer image ([`FreeBSD-13.2-RELEASE-amd64-bootonly.iso`][bootonly]) and save it to the local (container) filesystem.

### Stage 2: Build the installer

In the second stage of the build process, we copy the installer ISO from the first stage and extract the files using [xorriso], apply [our patches], and the regenerate an ISO image (again with xorriso). As part of the patching process, we apply the following changes:

[xorriso]: https://www.gnu.org/software/xorriso/
[our patches]: https://github.com/picocom-ng/freebsd-container/tree/main/installer_patches

- We fix the [bug in the installer][critical bug].
- We install a custom "dist" that contains some scripts for interacting with the container environment
- We override the default `rc.local` so that it doesn't prompt for a terminal type when logging in on the console (and just unilaterally set `TERM=xterm`).

You may be asking yourself, "why are you extracting the files with xorriso?" And the answer is that during the container build process we don't have the privileges to `mount -o loop,ro` the ISO image and copy the files from the mountpoint.

### Stage 3: Run the installer

In the third stage, we copy the generated install image from the previous stage, create a 2G disk image, and boot the installer using `qemu-system-x86_64`. We disable the graphic console, and optionally disable the text console as well if the `QEMU_INSTALL_QUIET` build argument is set to a non-empty value.

When the installation completes, we compute the sha256 checksum of the image and create a link to the image using that checksum, so we end up with something like:

```
/disk # ls -l /freebsd/
total 3456396
-rw-r--r--    2 root     root     1769668608 Aug 16 22:54 22b79f741f2d03b1cd44b2b4505de059e803ca83eb2398cff11371292b51b92f.img
-rw-r--r--    1 root     root           674 Aug 16 03:50 container-entrypoint.sh
-rw-r--r--    2 root     root     1769668608 Aug 16 22:54 freebsd.img
-rw-r--r--    1 root     root            65 Aug 16 22:54 freebsd.img.sha256
-rw-r--r--    1 root     root          1317 Aug 16 15:24 start-freebsd.sh
```

## Notes about networking

We need network connectivity for our FreeBSD virtual machine both when running the installer and when actually booting the finished container image. When setting up user mode networking, `qemu` will by default use the `10.0.2.0/24` network for addresses. If this happens to conflict with the address range used for the network on which the container is deployed it can lead to unexpected behavior (because for a given address like `10.0.2.2`, the container won't know if this is meant to address another container or the virtual machine).

A real solution to this problem would use logic like that used by tools like Podman and Docker, which will not select address ranges for which a non-default route exists on the host.

As a hacky workaround, I've configured the containers to default to using a subset of the [carrier grade nat] range, `100.64.0.0/10`. This will not typically conflict with an address range selected by Podman or Docker or a range used by a typical host or local network. The container image uses `100.64.0.0/24` by default, but this can be changed by setting the `QEMU_USER_NET` net build argument (at build time) or environment variable (at run time):

[carrier grade nat]: https://en.wikipedia.org/wiki/Carrier-grade_NAT

```
podman build --build-arg QEMU_USER_NET=192.168.71.0/24 -t freebsd .
```

## It's bigger on the inside!

We've installed FreeBSD onto a 2G image. When the installation is finished, that leaves us with less than 300MB of space, which is probably going to be insufficient for most use cases.

## Managing authentication
