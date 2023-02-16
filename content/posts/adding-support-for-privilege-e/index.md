---
categories: [tech]
aliases: ["/2019/04/26/adding-support-for-privilege-e/"]
title: "Adding support for privilege escalation to Ansible's docker connection driver"
date: "2019-04-26"
tags:
- "ansible"
- "pull-request"
---

**Update 2019-05-09** Pull request {{< pull-request "ansible/ansible/55816" >}} has merged, so you can now use `sudo` with the `docker` connection driver even when `sudo` is configured to require a password.

---

I often use Docker to test out Ansible playbooks.  While normally that works great, I recently ran into an unexpected problem with privilege escalation.  Given a simple playbook like this:

    ---
    - hosts: all
      gather_facts: false
      become: true
      tasks:
        - ping:

And an inventory like this:

    all:
      vars:
        ansible_user: example
        ansible_connection: docker
      hosts:
        server1:
          ansible_host: sudostuff_server1_1
        server2:
          ansible_host: sudostuff_server2_1
        server3:
          ansible_host: sudostuff_server3_1

And containers with `sudo` configured to require a password, Ansible would fail like this (note that I've configured Ansible to use the `debug` plugin for `stdout_callback`):

```
fatal: [server1]: FAILED! => {
    "changed": false,
    "rc": 1
}

MSG:

MODULE FAILURE
See stdout/stderr for the exact error


MODULE_STDERR:


We trust you have received the usual lecture from the local System
Administrator. It usually boils down to these three things:

    #1) Respect the privacy of others.
    #2) Think before you type.
    #3) With great power comes great responsibility.

[sudo via ansible, key=rzrfiifcqoggklmehivtcrrlnnbphwbp] password:
```

In the above output, you'll note that there are no actual errors, but unexpectedly we're seeing the privilege escalation prompt show up in the `stderr` of the command.  A quick search revealed bugs [#31759][] and [#53385], both of which confirm that privilege escalation simply doesn't work using the `docker` connection plugin.

[#53385]: https://github.com/ansible/ansible/issues/53385
[#31759]: https://github.com/ansible/ansible/issues/31759

## Use the source, Luke

{{< figure
src="sausage.jpg"
caption="Discovering how the sausage is made..."
width="400"
>}}

Looking at the source, I was surprised: while Ansible has individual plugins for different privilege escalation methods, it is entirely up to the individual connection plugin to implement the logic necessary to make use of these mechanisms. I had expected privilege escalation support to be implemented in the base connection plugin (`ConnectionBase` in `lib/ansible/plugins/connection/__init__.py`), but it's not.  So while the [ssh plugin][] has a fairly complex set of logic for handing the `become` prompt, and the [local plugin][] had a relatively simple solution, the `docker` connection had none.

Fortunately, in many ways the `docker` plugin is almost identical to the `local` plugin, which means that rather than doing actual work I was able to largely cut-and-paste the privilege escalation support from the `local` plugin into the `docker` plugin.  You can find this work in pull request {{< pull-request "ansible/ansible/55816" >}}.

[ssh plugin]: https://github.com/ansible/ansible/blob/devel/lib/ansible/plugins/connection/ssh.py
[local plugin]: https://github.com/ansible/ansible/blob/devel/lib/ansible/plugins/connection/local.py
