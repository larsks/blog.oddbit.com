---
categories: [tech]
aliases: ["/2015/10/09/running-ntp-in-a-container/"]
title: "Running NTP in a Container"
date: "2015-10-09"
tags:
  - docker
  - atomic
---

Someone asked on IRC about running ntpd in a container on [Atomic][],
so I've put together a small example.  We'll start with a very simple
`Dockerfile`:

[atomic]: http://www.projectatomic.io/

    FROM alpine
    RUN apk update
    RUN apk add openntpd
    ENTRYPOINT ["ntpd"]

I'm using the `alpine` image as my starting point because it's very
small, which makes this whole process go a little faster.  I'm
installing the [openntpd][] package, which provides the `ntpd` binary.

[openntpd]: http://www.openntpd.org/

By setting an `ENTRYPOINT` here, the `ntpd` binary will be started by
default, and any arguments passed to `docker run` after the image name
will be passed to `ntpd`.

We need to first build the image:

    # docker build -t larsks/ntpd .

And then we can try to run it:

    # docker run larsks/ntpd -h
    ntpd: unrecognized option: h
    usage: ntpd [-dnSsv] [-f file] [-p file]

That confirms that we can run the command.  Now we need to provide it
with a configuration file.  I looked briefly at [the ntpd.conf man
page][ntpd.conf], and I think we can get away with just providing the
name of an ntp server.  I created `/etc/ntpd.conf` on my atomic host
with the following content:

    servers pool.ntp.org

[ntpd.conf]: http://www.openbsd.org/cgi-bin/man.cgi/OpenBSD-current/man5/ntpd.conf.5?query=ntpd.conf

And then I tried running the container like this:

    docker run -v /etc/ntpd.conf:/etc/ntpd.conf larsks/ntpd -d -f /etc/ntpd.conf

The `-v` in the above command line makes `/etc/ntpd.conf` on the host
available as `/etc/ntpd.conf` inside the container.  This gets me:

    ntpd: can't set priority: Permission denied
    reset adjtime failed: Operation not permitted
    adjtimex (2) failed: Operation not permitted
    adjtimex adjusted frequency by 0.000000ppm
    fatal: privsep dir /var/empty could not be opened: No such file or directory
    Lost child: child exited
    dispatch_imsg in main: pipe closed
    Terminating

The first few errors ("Permission denied") mean that we need to pass
`--privileged` on the `docker run` command line.  Normally, Docker
runs containers with limited capabilities, but because an ntp service
needs to be able to set the time in the kernel it won't run in that
limited environment.

The "fatal: privsep dir /var/empty could not be opened" suggests we
need an empty directory at `/var/empty`.  With the above two facts in
mind, I tried:

    docker run --privileged -v /var/empty \
      -v /etc/ntpd.conf:/etc/ntpd.conf larsks/ntpd -d -f /etc/ntpd.conf -s

The `-s` on the end means "Try to set the time immediately at
startup."  This results in:

    adjtimex adjusted frequency by 0.000000ppm
    ntp engine ready
    reply from 104.131.53.252: offset -3.543963 delay 0.018517, next query 5s
    set local clock to Fri Oct  9 18:03:41 UTC 2015 (offset -3.543963s)
    reply from 198.23.200.19: negative delay -7.039390s, next query 3190s
    reply from 107.170.224.8: negative delay -6.983865s, next query 3139s
    reply from 209.118.204.201: negative delay -6.982698s, next query 3216s
    reply from 104.131.53.252: offset 3.523820 delay 0.018231, next query 8s

So that seems to work correctly.  To make this service persistent, I
can add `-d` to start the container in the background, and
`--restart=always` to make Docker responsible for restarting it if it
fails:

    docker run --privileged -v /var/empty \
      --restart=always -d \
      -v /etc/ntpd.conf:/etc/ntpd.conf larsks/ntpd -d -f /etc/ntpd.conf -s

And my Atomic host has an ntp service keeping the time in sync.

