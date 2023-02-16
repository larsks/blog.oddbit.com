---
aliases:
- /2016/02/07/folding-long-lines-in-ansible-inventory-/
- /post/2016-02-07-folding-long-lines-in-ansible-inventory-
categories:
- tech
date: '2016-02-07'
tags:
- ansible
- pull-request
title: Folding long lines in Ansible inventory files
---

If you have an Ansible inventory file that includes lots of per host
variables, it's not unusual for lines to get long enough that they
become unwieldly, particularly if you want to discuss them in an email
or write about them in some context (e.g., a blog post).

I've just submitted pull request [#14359][] to Ansible which
implements support for folding long lines using the INI-format
convention of using indent to mark extended logical lines.

With this patch in place, you can turn this:

    myhost ansible_host=a.b.c.d ansible_user=alice ansible_become=true ansible_ssh_extra_args="-F ~/.ssh/specialconfig" 

Into this:

    myhost
      ansible_host=a.b.c.d
      ansible_user=alice
      ansible_become=true
      ansible_ssh_extra_args="-F ~/.ssh/specialconfig" 

I think that's a lot easier to read.

If you think this is a good idea (or not!), feel free to comment on
the {{< pull-request "ansible/ansible/14359" >}}.  I considered (and implemented, then discarded)
using a backslash-based model instead...

    myhost \
      ansible_host=a.b.c.d \
      ...

...but I was swayed by the fact that the indent-style model is at
least documented [somewhere][configparser], and with the backslash
model it's easy to end up with something like this:

    myhost \
      ansible_host=a.b.c.d  # <--- OOOPS NO BACKSLASH
      ansible_user=alice \
      ansible_become=true

[#14359]: https://github.com/ansible/ansible/pull/14359
[configparser]: https://docs.python.org/3/library/configparser.html#supported-ini-file-structure