---
categories: [tech]
aliases: ["/2015/02/13/unpacking-docker-images/"]
title: Unpacking Docker images with Undocker
date: "2015-02-13"
tags:
  - docker
---

In some ways, the most exciting thing about [Docker][] isn't the ability
to start containers.  That's been around for a long time in various
forms, such as [LXC][] or [OpenVZ][].  What Docker brought to the
party was a convenient method of building and distributing the
filesystems necessary for running containers.  Suddenly, it was easy
to build a containerized service *and* to share it with other people.

[docker]: http://docker.com/
[lxc]: https://linuxcontainers.org/
[openvz]: http://openvz.org/Main_Page

I was taking a closer at the [systemd-nspawn][] command, which it
seems has been developing it's own set of container-related
superpowers recently, including a number of options for setting up the
network environment of a container.  Like Docker, `systemd-nspawn`
needs a filesystem on which to operate, but *unlike* Docker, there is
no convenient distribution mechanism and no ecosystem of existing
images.  In fact, the official documentation seems to assume that
you'll be building your own from scratch.  Ain't nobody got time for
that...

[systemd-nspawn]: http://www.freedesktop.org/software/systemd/man/systemd-nspawn.html

...but with that attracting Docker image ecosystem sitting right next
door, surely there was something we can do?

## The format of a Docker image

A Docker image is a tar archive that contains a top level
`repositories` files, and then a number of layers stored as
directories containing a `json` file with some metadata about the
layer and a tar file named `layer.tar` with the layer content.  For
example, if you `docker save busybox`, you get:

    4986bf8c15363d1c5d15512d5266f8777bfba4974ac56e3270e7760f6f0a8125/
    4986bf8c15363d1c5d15512d5266f8777bfba4974ac56e3270e7760f6f0a8125/VERSION
    4986bf8c15363d1c5d15512d5266f8777bfba4974ac56e3270e7760f6f0a8125/json
    4986bf8c15363d1c5d15512d5266f8777bfba4974ac56e3270e7760f6f0a8125/layer.tar
    511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158/
    511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158/VERSION
    511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158/json
    511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158/layer.tar
    df7546f9f060a2268024c8a230d8639878585defcc1bc6f79d2728a13957871b/
    df7546f9f060a2268024c8a230d8639878585defcc1bc6f79d2728a13957871b/VERSION
    df7546f9f060a2268024c8a230d8639878585defcc1bc6f79d2728a13957871b/json
    df7546f9f060a2268024c8a230d8639878585defcc1bc6f79d2728a13957871b/layer.tar
    ea13149945cb6b1e746bf28032f02e9b5a793523481a0a18645fc77ad53c4ea2/
    ea13149945cb6b1e746bf28032f02e9b5a793523481a0a18645fc77ad53c4ea2/VERSION
    ea13149945cb6b1e746bf28032f02e9b5a793523481a0a18645fc77ad53c4ea2/json
    ea13149945cb6b1e746bf28032f02e9b5a793523481a0a18645fc77ad53c4ea2/layer.tar
    repositories

In order to re-create the filesystem that would result from starting a
Docker container with this image, you need to unpack the `layer.tar`
files from the bottom up.  You can find the topmost layer in the
`repositories` file, which looks like this:

{
  "busybox": {
    "latest": "4986bf8c15363d1c5d15512d5266f8777bfba4974ac56e3270e7760f6f0a8125"
  }
}

From there, you can investigate the `json` file for each layer looking
for the `parent` tag.

## Introducing undocker

I wrote the [undocker][] command to extract all or part of the layers
of a Docker image onto the local filesystem.  In other words, if you
want to use the `busybox` Docker image, you can fetch and unpack the
image:

[undocker]: http://github.com/larsks/undocker/

    # docker pull busybox
    # docker save busybox | undocker -o busybox

This will first look in the `repositories` file for the `busybox`
entry with the `latest` tag, then build the necessary chain of layers
and unpack them in the correct order.

Once you have the filesystem extracted, you can boot it with
`systemd-nspawn`:

    # systemd-nspawn -D busybox /bin/sh
    Spawning container busybox on /root/busybox.
    Press ^] three times within 1s to kill container.
    Timezone America/New_York does not exist in container, not updating container timezone.
    Failed to copy /etc/resolv.conf to /root/busybox/etc/resolv.conf: Too many levels of symbolic links
    /bin/sh: can't access tty; job control turned off
    / # 

Undocker is able to extract specific layers from the image as well.
We can get a list of layers with the `--layers` option:

    $ docker save busybox | undocker --layers
    511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158
    df7546f9f060a2268024c8a230d8639878585defcc1bc6f79d2728a13957871b
    ea13149945cb6b1e746bf28032f02e9b5a793523481a0a18645fc77ad53c4ea2
    4986bf8c15363d1c5d15512d5266f8777bfba4974ac56e3270e7760f6f0a8125

And we can extract one or more specific layers with the `--layer`
(`-l`) option:

    $ docker save busybox |
      undocker -vi -o busybox -l ea13149945cb6b1e746bf28032f02e9b5a793523481a0a18645fc77ad53c4ea2
    INFO:undocker:extracting image busybox (4986bf8c15363d1c5d15512d5266f8777bfba4974ac56e3270e7760f6f0a8125)
    INFO:undocker:extracting layer ea13149945cb6b1e746bf28032f02e9b5a793523481a0a18645fc77ad53c4ea2

I'm using the `-i` (`--ignore-errors`) option here because this layer
contains a device node (`/dev/console`), and I am running this as an
unprivileged user.  Without the `-i` option, we would see:

    OSError: [Errno 1] Operation not permitted

A Docker image archive can actually contain multiple images, each with
multiple tags.  For a single image, `undocker` will default to
extracting the `latest` tag.  If the `latest` tag doesn't exist,
you'll see:

    # docker pull fedora:20
    # docker save fedora:20 | undocker -o fedora
    ERROR:undocker:failed to find image fedora with tag latest

You can specify an explicit tag in the same way you provide one to
Docker:

    # docker save fedora:20 | undocker -o fedora fedora:20

If an archive contains multiple images, you'll get a different error:

    # docker save busybox larsks/thttpd | undocker -o busybox
    ERROR:undocker:No image name specified and multiple images contained in archive

You can get a list of available images and tags with the `--list`
option:

    # docker save busybox larsks/thttpd | undocker --list
    larsks/thttpd: latest
    busybox: latest

    # docker save fedora | undocker --list
    fedora: heisenbug 20 21 rawhide latest

You can specify the image (and tag) to extract on the command line:

    # docker save busybox larsks/thttpd | undocker -o busybox busybox

