---
categories: [tech]
aliases: ["/2015/02/05/creating-minimal-docker-images/"]
title: Creating minimal Docker images from dynamically linked ELF binaries
date: "2015-02-05"
tags:
- docker
---

In this post, we'll look at a method for building minimal Docker
images for dynamically linked ELF binaries, and then at [a
tool][dockerize] for automating this process.

It is tempting, when creating a simple Docker image, to start with one
of the images provided by the major distributions.  For example, if
you need an image that provides `tcpdump` for use on your [Atomic][]
host, you might do something like:

[atomic]: http://www.projectatomic.io/

    FROM fedora
    RUN yum -y install tcpdump

And while this will work, you end up consuming 250MB for `tcpdump`.
In theory, the layering mechanism that Docker uses to build images
will reduce the practical impact of this (because other images based on
the `fedora` image will share the common layers), but in practice the
size is noticeable, especially if you often find yourself pulling this
image into a fresh environment with no established cache.

You can substantially reduce the space requirements for a Docker image
by including only those things that are absolutely necessary.  For
statically linked files, that may only be the binary itself, but the
situation is a little more complex for dynamically linked executables.
You might naively start with this (assuming that you had the `tcpdump`
binary in your local directory):

    FROM scratch
    COPY tcpdump /usr/sbin/tcpdump

If you were to build an image with this and tag it `tcpdump`...

    docker build -t tcpdump .

...and then try running it:

    docker run tcpdump

You would immediately see:

    no such file or directory
    FATA[0003] Error response from daemon: Cannot start container ...:
    no such file or directory 

And this is because the image is missing two things:

- The Linux dynamic runtime loader, and
- The shared libraries required by the `tcpdump` binary

The path to the appropriate loader is stored in the ELF binary in the
`.interp` section, which we can inspect using the `objdump` tool:

    $ objdump -s -j .interp tcpdump 

    tcpdump:     file format elf64-x86-64

    Contents of section .interp:
     400238 2f6c6962 36342f6c 642d6c69 6e75782d  /lib64/ld-linux-
     400248 7838362d 36342e73 6f2e3200           x86-64.so.2.    
        
Which tells us we need `/lib64/ld-linux-x86-64.so.2`.

We can use the `ldd` tool to get a list of shared libraries required
by the binary:

    $ ldd tcpdump
    linux-vdso.so.1 =>  (0x00007fffed1fe000)
    libcrypto.so.10 => /lib64/libcrypto.so.10 (0x00007fb2c05a3000)
    libpcap.so.1 => /lib64/libpcap.so.1 (0x00007fb2c0361000)
    libc.so.6 => /lib64/libc.so.6 (0x00007fb2bffa3000)
    libdl.so.2 => /lib64/libdl.so.2 (0x00007fb2bfd9f000)
    libz.so.1 => /lib64/libz.so.1 (0x00007fb2bfb89000)
    /lib64/ld-linux-x86-64.so.2 (0x00007fb2c09b7000)

If we copy all of the dependencies into a local directory, along with
the `tcpdump` binary itself, and use the following layout:

    Dockerfile
    usr/sbin/tcpdump
    lib64/libcrypto.so.10
    lib64/libpcap.so.1
    lib64/libc.so.6
    lib64/libdl.so.2
    lib64/libz.so.1
    lib64/ld-linux-x86-64.so.2

And the following Dockerfile content:

    FROM scratch
    COPY . /
    ENTRYPOINT ["/usr/sbin/tcpdump"]

And then we turn this into a Docker image and run it, we get:

    $ docker build -t tcpdump .
    [...]
    $ docker run tcpdump tcpdump -i eth0 -n
    tcpdump: Couldn't find user 'tcpdump'

Well, so let's create an `/etc/passwd` file with the `tcpdump` user
and add that to our collection:

    $ mkdir etc
    $ grep tcpdump /etc/passwd > etc/passwd
    $ grep tcpdump /etc/group > etc/group
    $ docker build -t tcpdump .
    $ docker run tcpdump tcpdump -i eth0 -n
    tcpdump: Couldn't find user 'tcpdump'

And *this* is because most programs don't reference files like
`/etc/passwd` directly, but instead delegate this task to the C
library, which relies on the [name service switch][nss] (nss)
mechanism to support multiple sources of information.  Let's add the
nss libraries necessary for supporting legacy files (`/etc/passwd`,
etc) and DNS for hostname lookups:

[nss]: http://www.gnu.org/software/libc/manual/html_node/Name-Service-Switch.html

- `lib64/libnss_files.so.2` -- this includes support the traditional
  files in `/etc`, such as `/etc/passwd`, `/etc/group`, and
  `/etc/hosts`.

- `lib64/libnss_dns.so.2` -- this supports hostname resolution via
  dns.

And we'll also need `/etc/nsswitch.conf` to go along with that:

    passwd:     files
    shadow:     files
    group:      files
    hosts:      files dns

After all this, we have:

    Dockerfile
    usr/sbin/tcpdump
    lib64/libcrypto.so.10
    lib64/libpcap.so.1
    lib64/libc.so.6
    lib64/libdl.so.2
    lib64/libz.so.1
    lib64/ld-linux-x86-64.so.2
    lib64/libnss_files.so.2
    lib64/libnss_dns.so.2
    etc/passwd
    etc/group
    etc/nsswitch.conf

Let's rebuild the image and run it one more time:

    $ docker build -t tcpdump .
    $ docker run tcpdump -i eth0 -n

And now, finally it runs.  Wouldn't it be nice if that process were
easier?

## Introducing Dockerize

[Dockerize][] is a tool that largely automates the above process.  To
build a minimal `tcpdump` image, for example, you would run:

[dockerize]: https://github.com/larsks/dockerize

    $ dockerize -u tcpdump -t tcpdump /usr/sbin/tcpdump

This would include the `tcpdump` user (`-u tcpdump`) from your local
system, as well as `/usr/sbin/tcpdump`, all it's dependencies, and
file-based nss support, and build an image tagged `tcpdump` (`-t
tcpdump`).  When you build an image from a single command, like this,
Dockerize will up that command as the Docker `ENTRYPOINT`, so you can
run it like this:

    $ docker run tcpdump -i eth0 -n

You can also build images containing multiple binaries.  For example:

    $ dockerize -t dockerizeme/xmltools \
        /usr/bin/xmllint \
        /usr/bin/xml2  \
        /usr/bin/2xml \
        /usr/bin/tidyp

In this case, you need to provide the command name when running the
image:

    $ docker run dockerizeme/xmltools tidyp -h

## Examples

You can find some scripts that generate marginally useful example
images in the [examples][] folder of the repository.

[examples]: https://github.com/larsks/dockerize/tree/master/examples

These are pushed into the [dockerizeme][] namespace on the Docker hub,
so you can, for example, get yourself a minimal webserver by running:

    $ docker run -v $PWD:/content -p 8888:80 dockerizeme/thttpd -d /content

And then browse to <http://localhost:8888> and see your current
directory.

[dockerizeme]: https://hub.docker.com/u/dockerizeme/

