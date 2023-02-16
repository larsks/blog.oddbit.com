---
categories: [tech]
aliases: ["/2014/07/21/tracking-down-a-kernel-bug-wit/"]
title: Tracking down a kernel bug with git bisect
date: "2014-07-21"
tags:
  - docker
  - kernel
  - git
---

After a recent upgrade of my Fedora 20 system to kernel 3.15.mumble, I
started running into a problem ([BZ 1121345][]) with my [Docker][]
containers.  Operations such as `su` or `runuser` would fail with the
singularly unhelpful `System error` message:

[bz 1121345]: https://bugzilla.redhat.com/show_bug.cgi?id=1121345
[docker]: https://www.docker.com/

    $ docker run -ti fedora /bin/bash
    bash-4.2# su -c 'uptime'
    su: System error

Hooking up something (like, say, `socat unix-listen:/dev/log -`) to
`/dev/log` revealed that the system was logging:

    Jul 19 14:31:18 su: PAM audit_log_acct_message() failed: Operation not permitted

Downgrading the kernel to 3.14 immediately resolved the problem,
suggesting that this was at least partly a kernel issue.  This seemed
like a great opportunity to play with the [git bisect][] command,
which uses a binary search to find which commit introduced a
particular problem.

[git bisect]: http://git-scm.com/docs/git-bisect

Unfortunately, between the version I knew to work correctly (3.14) and
the version I knew to have a problem (3.15) there were close to 15,000
commits, which seemed like a large space to search by hand.

Fortunately, `git bisect` can be easily automated via `git bisect run`
subcommand, which after checking out a commit will run a script to
determine if the current commit is "good" or "bad".  So all I have to
do is write a script...that's not so bad!

{{< figure src="ha-ha.jpg" width="300" >}}

It actually ended up being somewhat tricky.

## Testing kernels is hard

In order to test for this problem, I would need to use arbitrary
kernels generated during the `git bisect` operation to boot a system
functional enough to run docker, and then run docker and somehow
communicate the result of that test back to the build environment.

I started with the [Fedora 20 cloud image][cloud], which is nice and
small but still the same platform as my laptop on which I was
experiencing the problem.  I would need to correct a few things before
moving forward:

[cloud]: http://fedoraproject.org/get-fedora#clouds

The Fedora cloud images (a) do not support password authentication and
(b) expect a datasource to be available to [cloud-init][] (without
which you get errors on the console and potentially a delay waiting
for the `login:` prompt), so prior to using the image in this test I
made some changes by mounting it locally:

[cloud-init]: http://cloudinit.readthedocs.org/en/latest/

    # modprobe nbd max_part=8
    # qemu-nbd -c /dev/nbd0 Fedora-x86_64-20-20140407-sda.qcow2
    # mount /dev/nbd0p1 /mnt
    # systemd-nspawn -D /mnt

And then:

- I set a password for the `root` account and
- I removed the `cloud-init` package.

For this test I would be using the `qemu-system-x86_64` command
directly, rather than working through `libvirt` (`qemu` has options
for convenient debugging with `gdb`, and is also able to access the
filesystem as the calling `uid` whereas `libvirt` is typically running
as another user).

I would need to perform an initial `docker pull` in the image, which
meant I was going to need a functioning network, so first I had to set
up a network environment for qemu.

### Network configuration

I created a bridge interface named `qemu0` to be used by `qemu`.  I added
to `/etc/sysconfig/network-scripts/ifcfg-qemu0` the following:

    DEVICE=qemu0
    TYPE=Bridge
    ONBOOT=yes
    BOOTPROTO=none
    STP=no
    NAME="Bridge qemu0"
    IPADDR=192.168.210.1
    NETMASK=255.255.255.0

This is largely equivalent to the following, but persists after reboot:

    brctl addbr qemu0
    ip addr add 192.168.210.1/24 dev qemu0
    ip link set qemu0 up

I created a [tap][] interface named `linux0`:

[tap]: https://www.kernel.org/doc/Documentation/networking/tuntap.txt

    ip tuntap add dev linux0 mode tap user lars

And added it to the bridge:

    brctl addif qemu0 linux0

I also started up `dnsmasq` process listening on `qemu0` to provide
DNS lookup and DHCP service to qemu instances attached to this bridge.
The `dnsmasq` configuration looked like this:

    listen-address=192.168.210.1
    bind-interfaces
    dhcp-range=192.168.210.10,192.168.210.254

### Running qemu

With the network environment set up, I needed to figure out an
appropriate qemu command line.  This is what I finally ended up with,
in a script called `boot-kernel`:

    #!/bin/sh

    qemu-system-x86_64 -m 1024M \
      -drive file=fedora.img,if=virtio \
      -append "console=hvc0 root=/dev/vda1 selinux=0 $BOOT_ARGS" \
      -initrd initrd.img \
      -kernel arch/x86_64/boot/bzImage \
      -machine accel=kvm \
      -netdev tap,id=net0,ifname=linux0,script=no,downscript=no \
      -device virtio-net,netdev=net0,mac=52:54:00:c0:ff:ee \
      -chardev stdio,id=stdio,mux=on \
      -device virtio-serial-pci \
      -device virtconsole,chardev=stdio \
      -mon chardev=stdio \
      -fsdev local,id=fs0,path=$PWD,security_model=none \
      -device virtio-9p-pci,fsdev=fs0,mount_tag=kernel_src \
      -display none \
      $QEMU_ARGS

These lines set up the networking:

      -netdev tap,id=net0,ifname=linux0,script=no,downscript=no \
      -device virtio-net,netdev=net0,mac=52:54:00:c0:ff:ee \

These lines set up console on `stdin`/`stdout` and multiplex the
console with the qemu monitor:

      -chardev stdio,id=stdio,mux=on \
      -device virtio-serial-pci \
      -device virtconsole,chardev=stdio \
      -mon chardev=stdio \

These lines set up access to the current working directory as a `9p`
filesystem:

      -fsdev local,id=fs0,path=$PWD,security_model=none \
      -device virtio-9p-pci,fsdev=fs0,mount_tag=kernel_src \

Within the qemu instance, this lets me access my working directory with:

    mount -t 9p kernel_src /mnt

The `$BOOT_ARGS` and `$QEMU_ARGS` in the script allow me to modify the
behavior of the script by setting environment variables when calling
it, like this:

    QEMU_ARGS="-s" sh boot-kernel

### First boot

I tried to boot the image using my existing kernel and initrd from
`/boot`, and ran into a problem:

    [  184.060756] dracut-initqueue[218]: Warning: Could not boot.
    [  184.062855] dracut-initqueue[218]: Warning: /dev/ssd/root does not exist
             Starting Dracut Emergency Shell...
    Warning: /dev/ssd/root does not exist

    Generating "/run/initramfs/rdsosreport.txt"

    Entering emergency mode. Exit the shell to continue.

The what now?  `/dev/ssd/root` is the root device for my host system,
but wasn't anywhere in the kernel command line I used when booting
qemu.  It turns out that this was embedded in the initrd image in
`/etc/cmdline.d/90lvm.conf`.  After removing that file from the
image...

    # mkdir initrd
    # cd initrd
    # zcat /boot/initramfs-3.15.6-200.fc20.x86_64.img | cpio -id
    # rm -rf etc/cmdline.d
    # find . -print | cpio -o -Hcrc | gzip > ../initrd.img

...I was able to boot successfully and log in.

### I bet you thought we were done!

Modern systems are heavily modular.  Without access to a module tree
matching the kernel, I would be unable to successfully boot the
system, let alone use Docker.  Looking at which modules were loaded
when I ran `docker` with the above image, I set up a custom kernel
configuration that would permit me to boot and run docker without
requiring any loadable modules.  This would allow me to use the same
image for each kernel without needing to re-populate it with modules
each time I built a kernel.

The kernel configuration I ended up with is available [here][config].

[config]: kernel-config.txt

### Testing docker

The last step in this process is putting together something that tests
`docker` and exposes the result of that test to the build environment.
I added the following script to the image as `/root/docker-test`:

    #!/bin/sh

    grep NO_DOCKER_TEST /proc/cmdline && exit 0

    if [ -d /mnt/test_result ]; then
    docker run --rm -i fedora sh -c 'su -c true && echo OKAY || echo FAILED' \
      > /mnt/test_result/stdout \
      2> /mnt/test_result/stderr
    poweroff
    fi

This relies on the following entry in `/etc/fstab`:

    kernel_src /mnt 9p defaults 0 0

That mounts the build directory as a `9p` filesystem on `/mnt`.  This
allows us to write out test results to, e.g.,
`/mnt/test_result/stdout` and have that appear in the `test_result`
directory inside the kernel source.

This script is run at the end of the boot process via an entry in
`/etc/rc.d/rc.local`:

    #!/bin/sh

    sh /root/docker-test

Running the `boot-kernel` script without additional configuration will
cause the image to boot up, run the docker test, and then exit.

## Running git-bisect

At this point we have just about everything we need to start running
`git bisect`.  For the initial run, I'm going to use git tag `v3.14`
as the "known good" commit and `v3.15` as the "known bad" commit, so
we start `git bisect` like this:

    $ git bisect start v3.15 v3.14

Then we run `git bisect run sh bisect-test`, where `bisect-test` is
the following shell script:

    #!/bin/sh

    # Rebuild the kernel
    make olddefconfig
    make -j8

    # Clear out old test results and run the test
    rm -f test_result/{stdout,stderr}
    sh boot-kernel

    # Report results to git-bisect
    if grep OKAY test_result/stdout; then
      exit 0
    else
      exit 1
    fi

...and then we go out for a cup of coffee or something, because that's
going to take a while.

## Keep digging, Watson

The initial run of `git bisect` narrowed the change down to the
[following commit][b7d3622]:

[b7d3622]: https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/commit/?id=b7d3622

    commit b7d3622a39fde7658170b7f3cf6c6889bb8db30d
    Merge: f3411cb d8ec26d
    Author: Eric Paris <eparis@redhat.com>
    Date:   Fri Mar 7 11:41:32 2014 -0500

        Merge tag 'v3.13' into for-3.15
        
        Linux 3.13
        
        Conflicts:
            include/net/xfrm.h
        
        Simple merge where v3.13 removed 'extern' from definitions and the audit
        tree did s/u32/unsigned int/ to the same definitions.

As you can see (from the `Merge:` header), this is a merge commit, in
which an entire set of changes was joined into the `master` branch.
So while this commit is technically the first commit in which this
problem appears in the `master` branch...it is not actually the commit
that introduced the problem.

I was in luck, though, because looking at the history for the left
side of this branch (starting with [f3411cb][]) showed a series of
patches to the audit subsystem:

[f3411cb]: https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/commit/?id=f3411cb

    $ git log --oneline f3411cb
    f3411cb audit: whitespace fix in kernel-parameters.txt
    8626877 audit: fix location of __net_initdata for audit_net_ops
    4f06632 audit: remove pr_info for every network namespace
    262fd3a audit: Modify a set of system calls in audit class definitions
    3e1d0bb audit: Convert int limit uses to u32
    d957f7b audit: Use more current logging style
    b8dbc32 audit: Use hex_byte_pack_upper
    06bdadd audit: correct a type mismatch in audit_syscall_exit()
    1ce319f audit: reorder AUDIT_TTY_SET arguments
    0e23bac audit: rework AUDIT_TTY_SET to only grab spin_lock once
    3f0c5fa audit: remove needless switch in AUDIT_SET
    70249a9 audit: use define's for audit version

...etc.

I picked as a starting point the merge commit previous to [f3411cb][]:

    $ git log --merges -1
    commit fc582aef7dcc27a7120cf232c1e76c569c7b6eab
    Merge: 9175c9d 5e01dc7
    Author: Eric Paris <eparis@redhat.com>
    Date:   Fri Nov 22 18:57:08 2013 -0500

        Merge tag 'v3.12'
        
        Linux 3.12
        
        Conflicts:
            fs/exec.c

And ran `git bisect` again from [that commit][fc582ae] through to [f3411cb][]:

[fc582ae]: https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/commit/?id=fc582ae

    $ git bisect start f3411cb fc582ae
    $ git bisect run sh bisect-test

Which ultimately ended up with [this commit][33faba7]:

    33faba7fa7f2288d2f8aaea95958b2c97bf9ebfb is the first bad commit
    commit 33faba7fa7f2288d2f8aaea95958b2c97bf9ebfb
    Author: Richard Guy Briggs <rgb@redhat.com>
    Date:   Tue Jul 16 13:18:45 2013 -0400

        audit: listen in all network namespaces
        
        Convert audit from only listening in init_net to use register_pernet_subsys()
        to dynamically manage the netlink socket list.
        
        Signed-off-by: Richard Guy Briggs <rgb@redhat.com>
        Signed-off-by: Eric Paris <eparis@redhat.com>

Running `git bisect log` shows us what revisions were checked as part
of this process:

    # bad: [f3411cb2b2e396a41ed3a439863f028db7140a34] audit: whitespace fix in kernel-parameters.txt
    # good: [fc582aef7dcc27a7120cf232c1e76c569c7b6eab] Merge tag 'v3.12'
    git bisect start 'f3411cb' 'fc582ae'
    # bad: [ff235f51a138fc61e1a22dcb8b072d9c78c2a8cc] audit: Added exe field to audit core dump signal log
    git bisect bad ff235f51a138fc61e1a22dcb8b072d9c78c2a8cc
    # bad: [51cc83f024ee51de9da70c17e01ec6de524f5906] audit: add audit_backlog_wait_time configuration option
    git bisect bad 51cc83f024ee51de9da70c17e01ec6de524f5906
    # bad: [ae887e0bdcddb9d7acd8f1eb7b7795b438aa4950] audit: make use of remaining sleep time from wait_for_auditd
    git bisect bad ae887e0bdcddb9d7acd8f1eb7b7795b438aa4950
    # good: [2f2ad1013322c8f6c40fc6dafdbd32442fa730ad] audit: restore order of tty and ses fields in log output
    git bisect good 2f2ad1013322c8f6c40fc6dafdbd32442fa730ad
    # bad: [e789e561a50de0aaa8c695662d97aaa5eac9d55f] audit: reset audit backlog wait time after error recovery
    git bisect bad e789e561a50de0aaa8c695662d97aaa5eac9d55f
    # bad: [33faba7fa7f2288d2f8aaea95958b2c97bf9ebfb] audit: listen in all network namespaces
    git bisect bad 33faba7fa7f2288d2f8aaea95958b2c97bf9ebfb
    # first bad commit: [33faba7fa7f2288d2f8aaea95958b2c97bf9ebfb] audit: listen in all network namespaces

The commit found by `git bisect` seems like a reasonable candidate;
it's a patch against the audit subsystem and has something to do with
namespaces, which are central to Docker's proper operation.

## Debugging the problem

We can boot the kernel built from 33faba7 with the `boot-kernel`
script, adding the `-s` argument to qemu to start a `gdbserver` on
port `1234`:

    sh BOOT_ARGS=NO_DOCKER_TEST QEMU_ARGS="-s" boot-kernel

> A caveat about attaching to qemu with gdb: qemu has a `-S` option
> that will cause the virtual machine to halt at startup, such that
> you can attach before it starts booting and -- in theory -- set
> breakpoints in the early boot process.  In practice this doesn't
> work well at all (possibly because the vm switches from 32- to
> 64-bit operation during the boot process, which makes gdb unhappy).
> You're better off attaching after the kernel has booted.

In another window, we attach `gdb` to the running `qemu` process:

    $ gdb vmlinux
    Reading symbols from vmlinux...done.
    (gdb) target remote :1234
    Remote debugging using :1234
    native_safe_halt () at /home/lars/src/linux/arch/x86/include/asm/irqflags.h:50
    50	}
    (gdb) 

I know we're getting the `EPERM` in response to sending audit
messages.  Looking through the code in `kernel/audit.c`, the
`audit_receive_msg` seems like a reasonable place to start poking
about.  At the beginning of `audit_receive_msg`, I see the following
code:

    err = audit_netlink_ok(skb, msg_type);
    if (err)
      return err;

So let's set a breakpoint there if `audit_netlink_ok()` returns an
error:

    (gdb) br kernel/audit.c:752 if (err != 0)

And let our qemu process continue running:

    (gdb) continue
    Continuing.

Inside the qemu instance I start docker:

    -bash-4.2# docker run -it fedora /bin/su -c uptime

And eventually `gdb` hits the breakpoint:

    Breakpoint 1, audit_receive_msg (nlh=0xffff88003819a400, 
        skb=0xffff880038044300) at kernel/audit.c:752
    752		if (err)

If I look at the value of `err` at this point:

    (gdb) print err
    $1 = -1

That it is, in fact, `-EPERM`, which suggests we're on the right
track.  Taking a closer look at `audit_netlink_ok()`, it's obvious
that there are only three places where it can return `-EPERM`.  I
tried setting some breakpoint in this function but they weren't
working correctly, probably due to to optimizations performed when
compiling the kernel.  So instead of `gdb`, in this step we just add a
bunch of `pr_err()` statements to print out debugging information on
the console:

    if ((current_user_ns() != &init_user_ns) ||
        (task_active_pid_ns(current) != &init_pid_ns)) {
      pr_err("currnet_user_ns() check failed\n");
      return -EPERM;
    }
    .
    .
    .
    case AUDIT_MAKE_EQUIV:
      if (!capable(CAP_AUDIT_CONTROL)) {
        pr_err("CAP_AUDIT_CONTROL check failed\n");
        err = -EPERM;
      }
      break;
    case AUDIT_USER:
    .
    .
    .
    case AUDIT_FIRST_USER_MSG ... AUDIT_LAST_USER_MSG:
    case AUDIT_FIRST_USER_MSG2 ... AUDIT_LAST_USER_MSG2:
      if (!capable(CAP_AUDIT_WRITE)) {
        pr_err("CAP_AUDIT_WRITE check failed\n");
        err = -EPERM;
      }
      break;

With these in place, if I run the `docker` command again I see:

    [   12.239860] currnet_user_ns() check failed
    su: System error

It looks like we've found out where it's failing!  Of course, we're
checking code right now that is several commits behind v3.15, so let's
take a look the same function in the 3.15 release:

    $ git checkout v3.15

Looking at `audit_netlink_ok` in `kernel/audit.c`, it looks as if that
initial check has changed:

        /* Only support initial user namespace for now. */
        /*
         * We return ECONNREFUSED because it tricks userspace into thinking
         * that audit was not configured into the kernel.  Lots of users
         * configure their PAM stack (because that's what the distro does)
         * to reject login if unable to send messages to audit.  If we return
         * ECONNREFUSED the PAM stack thinks the kernel does not have audit
         * configured in and will let login proceed.  If we return EPERM
         * userspace will reject all logins.  This should be removed when we
         * support non init namespaces!!
         */
        if (current_user_ns() != &init_user_ns)
                return -ECONNREFUSED;

So let's insert our print statements into this version of the code and
see if we get the same behavior:

    if (current_user_ns() != &init_user_ns) {
      pr_err("current_user-ns() check failed\n");
      return -ECONNREFUSED;
    }
    .
    .
    .
    case AUDIT_MAKE_EQUIV:
      /* Only support auditd and auditctl in initial pid namespace
       * for now. */
      if ((task_active_pid_ns(current) != &init_pid_ns)) {
        pr_err("init_pid_ns check failed\n");
        return -EPERM;
      }

      if (!netlink_capable(skb, CAP_AUDIT_CONTROL)) {
        pr_err("CAP_AUDIT_CONTROL check failed\n");
        err = -EPERM;
      }
      break;
    .
    .
    .
    case AUDIT_USER:
    case AUDIT_FIRST_USER_MSG ... AUDIT_LAST_USER_MSG:
    case AUDIT_FIRST_USER_MSG2 ... AUDIT_LAST_USER_MSG2:
      if (!netlink_capable(skb, CAP_AUDIT_WRITE)) {
        pr_err("CAP_AUDIT_WRITE check failed\n");
        err = -EPERM;
      }
      break;

Running the v3.15 kernel, I see:

    [   26.273992] audit: CAP_AUDIT_WRITE check failed
    su: System error

So it looks like the intial failure in `audit_netlink_ok()` was fixed,
but we're stilling failing the `CAP_AUDIT_WRITE` check.

### Summary 

What's going on here?

Prior to [33faba7][], audit messages were only accepted in the main
network namespace.  Inside other network namespaces, processes sending
audit messages would simply receive `ECONNREFUSED`.  For example, this
is the result of using `strace` on that `docker run` command in a
pre-[33faba7][] kernel:

    539   sendto(3, "...authentication acct=\"root\" exe=\"/usr/bin/su\" hostname=? a"...,
          112, 0, {sa_family=AF_NETLINK, pid=0, groups=00000000}, 12) = -1 ECONNREFUSED (Connection refused)

With [33faba7][], audit messages are now accepted inside network
namespaces. This means that instead of simply getting `ECONNREFUSED`,
messages must pass the kernel capability check.  I spoke with some of
the audit subsystem maintainers (including Richard Guy Briggs, the
author of this patch series), and the general consensus is that "if
you want to write audit messages you need `CAP_AUDIT_WRITE`".

So while this patch did change the behavior of the kernel from the
perspective of container tools such as Docker, the fix needs to be in
the tool creating the namespaces.

[33faba7]: https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/commit/?id=33faba7

## Results

This issue was reported against Fedora in [BZ 1121345][] and [BZ
1119849][].  This issue was also reported against Docker in [GHI 6345][]
and [GHI 7123][].

This problem has been corrected upstream in {{< pull-request "dotcloud/docker/7179" >}}.

Package [docker-io-1.0.0-9.fc20][docker-io-package], which includes
the above fix, is now available for Fedora 20 (and Fedora 19).

[bz 1119849]: https://bugzilla.redhat.com/show_bug.cgi?id=1119849
[ghi 6345]: https://github.com/dotcloud/docker/issues/6345
[ghi 7123]: https://github.com/dotcloud/docker/issues/7123
[docker-io-package]: https://admin.fedoraproject.org/updates/FEDORA-2014-8877/docker-io-1.0.0-9.fc20

