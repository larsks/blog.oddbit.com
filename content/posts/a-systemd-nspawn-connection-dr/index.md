---
aliases:
- /2016/02/08/a-systemd-nspawn-connection-driver-for-a/
- /post/2016-02-08-a-systemd-nspawn-connection-driver-for-a
categories:
- tech
date: '2016-02-08'
tags:
- ansible
- systemd
- pull-request
title: A systemd-nspawn connection driver for Ansible
---

I wrote [earlier][] about [systemd-nspawn][], and how it can take much
of the fiddly work out of setting up functional `chroot` environments.
I'm a regular [Ansible][] user, and I wanted to be able to apply some
of those techniques to my playbooks.

[earlier]: {{< ref "systemd-nspawn-for-fun-and-wel" >}}
[systemd-nspawn]: https://www.freedesktop.org/software/systemd/man/systemd-nspawn.html

Ansible already has a `chroot` module, of course, but for some
situations -- such as targeting an emulated `chroot` environment --
that just means a lot of extra work.  Using `systemd-nspawn` makes
this trivial.

I've submitted {{< pull-request "ansible/ansible/14334" >}} to the Ansible project,
which introduces a new connection driver named `nspawn`.  It acts very
much like the `chroot` driver, but it adds a few new configuration
options:

- `ansible_nspawn_args` -- analagous to `ansible_ssh_args`, setting
  this will override the arguments that are passed to `systemd-nspawn`
  by default.

- `ansible_nspawn_extra_args` -- analgous to `ansible_ssh_extra_args`,
  setting this will *append* the values to the default
  `systemd-nspawn` command line.

## Advantages over chroot

Let's say we had a Fedora filesystem mounted on `/fedora` and we want
to run the following playbook:

    - hosts: /fedora
      tasks:
        - raw: dnf -y install python libselinux-python python2-dnf
        - dnf:
            name: git
            state: installed

Using the `chroot` driver, we get:

    $ sudo ansible-playbook -i /fedora, -c chroot playbook.yml

    PLAY ***************************************************************************

    TASK [raw] *********************************************************************
    fatal: [/fedora]: FAILED! => {"changed": false, "failed": true, "rc": -6, "stderr": "Fatal Python error: Failed to open /dev/urandom\n", "stdout": "", "stdout_lines": []}

Adding the necessary tasks to our playbook to set up the chroot
environment properly will add a lot of additional complexity and will
make the playbook substantially less generic.  Now compare that to the
result of running the same playbook using the `nspawn` driver:

    $ sudo ansible-playbook -i /fedora, -c nspawn playbook.yml

    PLAY ***************************************************************************

    TASK [raw] *********************************************************************
    ok: [/fedora]

    TASK [dnf] *********************************************************************
    changed: [/fedora]

    PLAY RECAP *********************************************************************
    /fedora                       : ok=2    changed=1    unreachable=0    failed=0   

## Ansible in emulation

By taking advantage of `ansible_nspawn_extra_args` you can create
more complex containers.  For example, in my [last post][earlier] on
`systemd-nspawn` I showed how to start a container for a different
architecture through the use of QEMU user-mode emulation.  We can
apply the same idea to Ansible with an inventory entry like this:

    target
      ansible_host=/fedora
      ansible_connection=nspawn
      ansible_nspawn_extra_args="--bind /usr/bin/qemu-arm"

The above will allow you to run a playbook against a filesystem
containing ARM architecture binaries, even though you're running on an
x86_64 host.

[ansible]: http://ansible.com/
