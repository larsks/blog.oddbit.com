---
aliases:
- /2015/10/19/stupid-ansible-tricks-running-a-role-from-the-command-line/
- /post/2015-10-19-stupid-ansible-tricks-running-a-role-from-the-command-line
categories:
- tech
date: '2015-10-19'
tags:
- ansible
title: 'Stupid Ansible Tricks: Running a role from the command line'
---

When writing [Ansible][] roles I occasionally want a way to just run a
role from the command line, without having to muck about with a
playbook.  I've seen [similar][1] [requests][2] on the mailing lists
and on irc.

[ansible]: http://www.ansible.com/
[1]: https://groups.google.com/forum/#!topic/ansible-project/h-SGLuPDRrs
[2]: https://groups.google.com/forum/#!topic/ansible-devel/GqzZ6zsn6eY

I've thrown together a quick wrapper that will allow you (and me!) to
do exactly that, called [ansible-role][].  The `--help` output looks
like this:

[ansible-role]: http://github.com/larsks/ansible-role

    usage: ansible-role [-h] [--verbose] [--gather] [--no-gather]
                        [--extra-vars EXTRA_VARS] [-i INVENTORY] [--hosts HOSTS]
                        [--sudo] [--become] [--user USER]
                        role

    positional arguments:
      role

    optional arguments:
      -h, --help            show this help message and exit
      --verbose, -v
      --gather, -g
      --no-gather, -G
      --extra-vars EXTRA_VARS, -e EXTRA_VARS

    Inventory:
      -i INVENTORY, --inventory INVENTORY
      --hosts HOSTS, -H HOSTS

    Identity:
      --sudo, -s
      --become, -b
      --user USER, -u USER

## Example

If you have a role `roles/testrole` that contains the following in
`tasks/main.yml`:

    - name: figure out who I am
      command: whoami
      register: whoami

    - name: show who I am
      debug:
        msg: "I am {{whoami.stdout}}"

You could run it like this:

    $ ansible-role testrole -i localhost,

Which would get you:

    PLAY ***************************************************************************

    TASK [setup] *******************************************************************
    ok: [localhost -> localhost]

    TASK [testrole : figure out who I am] ******************************************
    changed: [localhost -> localhost]

    TASK [testrole : show who I am] ************************************************
    ok: [localhost -> localhost] => {
        "changed": false, 
        "msg": "I am lars"
    }

    PLAY RECAP *********************************************************************
    localhost                  : ok=3    changed=1    unreachable=0    failed=0   

You can use the `-b` (formerly `-s`) flag to enable privilege
escalation via `sudo`:

    $ ansible-role testrole -i localhost, -s

Which will work as expected:

    TASK [testrole : show who I am] ************************************************
    ok: [localhost -> localhost] => {
        "changed": false, 
        "msg": "I am root"
    }

The `ansible-role` command does not currently provide proxy arguments
for *all* of the options supported by `ansible-playbook`, but
hopefully it supports enough to be useful.  If you have bug reports or
pull requests, feel free to leave them [on the GitHub
repository][github].

[github]: http://github.com/larsks/ansible-role/issues