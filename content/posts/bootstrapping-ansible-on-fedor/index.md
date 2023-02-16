---
aliases:
- /2015/10/15/bootstrapping-ansible-on-fedora-23/
- /post/2015-10-15-bootstrapping-ansible-on-fedora-23
categories:
- tech
date: '2015-10-15'
tags:
- ansible
- fedora
title: Bootstrapping Ansible on Fedora 23
---

If you've tried running [Ansible][] against a [Fedora][] 23 system,
you may have run into the following problem:

[ansible]: http://ansible.com/
[fedora]: http://fedoraproject.org/

    fatal: [myserver]: FAILED! => {"changed": false, "failed": true,
    "msg": "/bin/sh: /usr/bin/python: No such file or directory\r\n",
    "parsed": false}

Fedora has recently made the switch to only including Python 3 on the
base system (at least for the [cloud][] variant), while Ansible still
requires Python 2.  With Fedora 23, Python 3 is available as
`/usr/bin/python3`, and `/usr/bin/python` is only available if you
have installed the Python 2 interpreter.

[cloud]: https://getfedora.org/en/cloud/prerelease/

This is not an insurmountable problem; Ansible's [raw][] module can be
used to run arbitrary commands on a remote host without requiring an
installed Python interpreter.  This gives us everything we need to
bootstrap the remote environment.

[raw]: http://docs.ansible.com/ansible/raw_module.html

The simplest playbook might look something like:

    - hosts: all
      tasks:
        - name: install packages for ansible support
          raw: dnf -y -e0 -d0 install python python-dnf

(The `python-dnf` package is required if you want to install packages
using the `dnf` module.)

So you drop this into a playbook and run it and...it still fails, with
the same error.  This is because Ansible will, by default, attempt to
gather facts from the remote host by running the `setup` module, which
requires Python.  So we modify our playbook to look like this:

    - hosts: all
      gather_facts: false
      tasks:
        - name: install packages for ansible support
          raw: dnf -y -e0 -d0 install python python-dnf

Setting `gather_facts: false` inhibits this initial fact collection;
with this change, the playbook should run successfully:

    $ ansible-playbook playbook.yml
    PLAY ***************************************************************************

    TASK [install packages for ansible support] ************************************
    ok: [myserver -> localhost]

    PLAY RECAP *********************************************************************
    myserver                   : ok=1    changed=0    unreachable=0    failed=0   

Having installed the basics, you can now use many of the standard
Ansible modules:

    - hosts: all
      gather_facts: true
      tasks:
        - lineinefile:
            dest: /etc/hosts
            line: "{{ansible_eth0.ipv4.address}} {{inventory_hostname}}"
            regexp: "{{inventory_hostname}}"
        - package:
            name: git
            state: present

As the above example demonstrates, now that the necessary Python stack
is installed on the remote Fedora 23 host, Ansible is is able to
gather [facts][] about the host that can be used in tasks, templates,
etc.

Note that with the `raw` module I had to use the `dnf` command
explicitly, while in the above playbook I can use the `package` module
for package installation, which relies on available facts to determine
the correct package module.

[facts]: http://docs.ansible.com/ansible/playbooks_variables.html#information-discovered-from-systems-facts