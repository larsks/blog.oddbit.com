---
categories: [tech]
aliases: ["/2015/01/18/docker-vs-privatetmp/"]
title: Docker vs. PrivateTmp
date: "2015-01-18"
tags:
  - docker
  - systemd
  - namespaces
---

While working with Docker [the other day][], I ran into an
undesirable interaction between Docker and [systemd][] services that
utilize the `PrivateTmp` directive.

[systemd]: http://www.freedesktop.org/wiki/Software/systemd/
[the other day]: {{< ref "running-novalibvirt-and-novado" >}}

The [PrivateTmp][] directive, if `true`, "sets up a new file system
namespace for the executed processes and mounts private `/tmp` and
`/var/tmp` directories inside it that is not shared by processes outside
of the namespace".  This is a great idea from a [security
perspective][], but can cause some unanticipated consequences.

[privatetmp]: http://www.freedesktop.org/software/systemd/man/systemd.exec.html#PrivateTmp=
[security perspective]: https://danwalsh.livejournal.com/51459.html

## The problem in a nutshell

1. Start a Docker container:

        # cid=$(docker run -d larsks/thttpd)
        # echo $cid
        e68df3f45d6151259ce84a0e467a3117840084e99ef3bbc654b33f08d2d6dd62

1. See the `devicemapper` mountpoint created by Docker for the
   container:

        # grep devicemapper/mnt /proc/mounts
        /dev/mapper/docker-253:6-98310-e68df3f45d6151259ce84a0e467a3117840084e99ef3bbc654b33f08d2d6dd62 /var/lib/docker/devicemapper/mnt/e68df3f45d6151259ce84a0e467a3117840084e99ef3bbc654b33f08d2d6dd62 ext4 rw,context="system_u:object_r:svirt_sandbox_file_t:s0:c261,c1018",relatime,discard,stripe=16,data=ordered 0 0

1. Now restart a service -- any service! -- that has
   `PrivateTmp=true`:

        # systemctl restart systemd-machined

1. Get the PID for that service:

        # systemctl status systemd-machined | grep PID
         Main PID: 18698 (systemd-machine

1. And see that the mount created by the Docker "devicemapper" storage
   driver is visible inside the mount namespace for this process:

        # grep devicemapper/mnt /proc/18698/mounts
        /dev/mapper/docker-253:6-98310-e68df3f45d6151259ce84a0e467a3117840084e99ef3bbc654b33f08d2d6dd62 /var/lib/docker/devicemapper/mnt/e68df3f45d6151259ce84a0e467a3117840084e99ef3bbc654b33f08d2d6dd62 ext4 rw,context="system_u:object_r:svirt_sandbox_file_t:s0:c261,c1018",relatime,discard,stripe=16,data=ordered 0 0

1. Attempt to destroy the container:

        # docker rm -f $cid

1. Watch Docker fail to destroy the container because it is unable to
   remove the mountpoint directory:

        Jan 17 22:43:03 pk115wp-lkellogg docker-1.4.1-dev[18239]:
        time="2015-01-17T22:43:03-05:00" level="error" msg="Handler for DELETE
        /containers/{name:.*} returned error: Cannot destroy container e68df3f45d61:
        Driver devicemapper failed to remove root filesystem
        e68df3f45d6151259ce84a0e467a3117840084e99ef3bbc654b33f08d2d6dd62: Device is
        Busy"

1. Because while that mount is gone from the global namespace:

        # grep devicemapper/mnt /proc/mounts

1.  It still exists inside the mount namespace for the service we restarted:

        # grep devicemapper/mnt /proc/18698/mounts
        /dev/mapper/docker-253:6-98310-e68df3f45d6151259ce84a0e467a3117840084e99ef3bbc654b33f08d2d6dd62 /var/lib/docker/devicemapper/mnt/e68df3f45d6151259ce84a0e467a3117840084e99ef3bbc654b33f08d2d6dd62 ext4 rw,context="system_u:object_r:svirt_sandbox_file_t:s0:c261,c1018",relatime,discard,stripe=16,data=ordered 0 0

1. To resolve this problem, restart the service holding the mount open:

       # systemctl restart systemd-machined

Now the mountpoint can be deleted.

## It's not just Docker

While I ran into this problem while working with Docker, there is
nothing particularly Docker-specific about the problem.  You can
replicate this behavior by hand without involving either `systemd` or
Docker:

1. Create a parent mountpoint, and make it private:

        # mkdir /tmp/parent /tmp/parent-backing
        # mount --bind --make-private /tmp/parent-backing /tmp/parent

1. Create a private mount on a directory *inside* `/tmp/parent`:

        # mkdir /tmp/testmount /tmp/parent/mnt
        # mount --bind --make-private /tmp/testmount /tmp/parent/mnt
        # grep /tmp/parent/mnt /proc/self/mounts
        tmpfs /tmp/parent/mnt tmpfs rw,seclabel 0 0

1. In another window, create a new mount namespace using `unshare`:

        # unshare -m env PS1='unshare# ' bash
        unshare#

1. Unmount `/tmp/parent/mnt` in the global namespace:

        # umount /tmp/parent/mnt
        # grep /tmp/parent/mnt /proc/self/mounts
        #

1. Try to delete the mountpoint directory:

        # rmdir /tmp/parent/mnt
        rmdir: failed to remove ‘/tmp/parent/mnt’: Device or resource busy

1. See that the mount still exists in your `unshare` namespace:

        unshare# grep /tmp/parent/mnt /proc/self/mounts
        tmpfs /tmp/parent/mnt tmpfs rw,seclabel 0 0

## So what's going on here?

To understand what's going on in these examples, you probably want to
start by at least glancing through the [sharedsubtree.txt][] kernel
documentation.

[sharedsubtree.txt]: https://www.kernel.org/doc/Documentation/filesystems/sharedsubtree.txt

The Docker `devicemapper` driver creates a *private* mount on
`/var/lib/docker/devicemapper`.  A *private* mount is one that does
not propagate mount operations between parent and child mount
namespaces.

Container filesystems are mounted underneath
`/var/lib/docker/devicemapper/mnt`, e.g:

        /dev/mapper/docker-253:6-98310-e68df3f45d6151259ce84a0e467a3117840084e99ef3bbc654b33f08d2d6dd62 /var/lib/docker/devicemapper/mnt/e68df3f45d6151259ce84a0e467a3117840084e99ef3bbc654b33f08d2d6dd62 ext4 rw,context="system_u:object_r:svirt_sandbox_file_t:s0:c261,c1018",relatime,discard,stripe=16,data=ordered 0 0

When you create a new mount namespace as a child of the global mount
namespace, either via the `unshare` command or by starting a systemd
service with `PrivateTmp=true`, it inherits these private mounts.
When Docker unmounts the the container filesystem in the global
namespace, the fact that the `/var/lib/docker/devicemapper` mountpoint
is marked *private* means that the unmount operation does not
propagate to other namespaces.

## The solution

The simplest solution to this problem is to set the `MountFlags=slave`
option in the `docker.service` file:

    MountFlags=slave

This will cause SystemD to run Docker in a cloned mount namespace and
sets the `MS_SLAVE` flag on all mountpoints; it is effectively
equivalent to:

    # unshare -m
    # mount --make-rslave /

With this change, mounts performed by Docker will not be visible in
the global mount namespace, and they will thus not propagate into the
mount namespaces of other services.

## Not necessarily the solution

There was an [attempt to fix this problem][] committed to the Fedora
`docker-io` package that set `MountFlags=private`.  This will prevent
the symptoms I originally encountered, in which Docker is unable to
remove a mountpoint because it is still held open by another mount
namespace...

[attempt to fix this problem]: http://pkgs.fedoraproject.org/cgit/docker-io.git/commit/?id=6c9e373ee06cb1aee07d3cae426c46002663010d

...but it will result in behavior that might be confusing to a system
administrator.  Specifically, mounts made in the global mount
namespace after Docker starts will not be visible to Docker
containers.  This means that if you were to make a remote filesystem
available on your Docker host:

    # mount my-fileserver:/vol/webcontent /srv/content

And then attempt to bind that into a Docker container as a volume:

    # docker run -v /srv/content:/content larsks/thttpd -d /content

Your content would not be visible.  The mount of
`my-fileserver:/vol/webcontent` would not propagate from the global
namespace into the Docker mount namespace because of the *private*
flag.

## Thanks

I had some help figuring this out.  Thanks to [Lennart Poettering],
Andrey Borzenkov, and [Colin Walters][].

[lennart poettering]: https://en.wikipedia.org/wiki/Lennart_Poettering
[colin walters]: http://blog.verbum.org/


