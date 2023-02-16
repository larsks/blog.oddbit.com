---
aliases:
- /2018/01/24/safely-restarting-an-openstack-server-wi/
- /post/2018-01-24-safely-restarting-an-openstack-server-wi
categories:
- tech
date: '2018-01-24'
tags:
- ansible
- openstack
title: Safely restarting an OpenStack server with Ansible
---

The other day on [#ansible][], someone was looking for a way to safely
shut down a Nova server, wait for it to stop, and then start it up
again using the `openstack` cli.  The first part seemed easy:

[#ansible]: http://docs.ansible.com/ansible/latest/community.html#irc-channel

    - hosts: myserver
      tasks:
        - name: shut down the server
          command: poweroff
          become: true

...but that will actually fail with the following result:

    TASK [shut down server] *************************************
    fatal: [myserver]: UNREACHABLE! => {"changed": false, "msg":
    "Failed to connect to the host via ssh: Shared connection to
    10.0.0.103 closed.\r\n", "unreachable": true}

This happens because running `poweroff` immediately closes Ansible's
ssh connection.  The workaround here is to use a "fire-and-forget"
[asynchronous task][]:

[asynchronous task]: http://docs.ansible.com/ansible/latest/playbooks_async.html

    - hosts: myserver
      tasks:
         - name: shut down the server
           command: poweroff
           become: true
           async: 30
           poll: 0

The `poll: 0` means that Ansible won't wait around to check the result
of this task.  Control will return to ansible immediately, so our
playbook can continue without errors resulting from the closed
connection.

Now that we've started the shutdown process on the host, how do we
wait for it to complete?  You'll see people solve this with a
[pause][] task, but that's fragile because the timing there can be
tricky to get right.

[pause]: http://docs.ansible.com/ansible/latest/pause_module.html

Another option is to use something like Ansible's [wait_for][] module.
For example, we could wait for `sshd` to become unresponsive:

[wait_for]: http://docs.ansible.com/ansible/latest/wait_for_module.html

    - name: wait for server to finishing shutting down
      wait_for:
        port: 22
        state: stopped

Be this is really just checking whether or not `sshd` is listening for
a connection, and `sshd` may shut down long before the system shutdown
process completes.

The best option is to ask Nova.  We can query Nova for information
about a server using the Ansible's [os_server_facts][] module.  Like
the other OpenStack modules, this uses [os-client-config][] to find
authentication credentials for your OpenStack environment.  If you're
not explicitly providing authentication information in your playbook,
the module will use the `OS_*` environment variables that are commonly
used with the OpenStack command line tools.

[os_server_facts]: http://docs.ansible.com/ansible/latest/os_server_facts_module.html
[os-client-config]: https://docs.openstack.org/os-client-config/latest/

The `os_server_facts` module creates an `openstack_servers` fact, the
value of which is a list of dictionaries which contains keys like
`status`, which is the one in which we're interested.  A running
server has `status == "ACTIVE"` and a server that has been powered off
has `status == "SHUTOFF`.

Given the above, the "wait for shutdown" task would look something
like the following:

    - hosts: localhost
      tasks:
         - name: wait for server to stop
           os_server_facts:
             server: myserver
           register: results
           until: openstack_servers.0.status == "SHUTOFF"
           retries: 120
           delay: 5

You'll note that I'm targeting `localhost` right now, because my local
system has access to my OpenStack environment and I have the necessary
credentials in my environment.  If you need to run these tasks
elsewhere, you'll want to read up on how to provide credentials in
your playbook.

This task will retry up to `120` times, waiting `5` seconds between
tries, until the server reaches the desired state.

Next, we want to start the server back up.  We can do this using
the [os_server_action][] module, using the `start` action.  This task
also runs on `localhost`:

[os_server_action]: http://docs.ansible.com/ansible/latest/os_server_action_module.html

     - name: start the server
       os_server_action:
         server: larstest
         action: start

Finally, we want to wait for the host to come back up before we run
any additional tasks on it.  In this case, we can't just look at the
status reported by Nova: the host will be `ACTIVE` from Nova's
perspective long before it is ready to accept `ssh` connections.  Nor
can we use the `wait_for` module, since the `ssh` port may be open
before we are actually able to log in.  The solution to this is the
[wait_for_connection][] module, which waits until Ansible is able to
successful execute an action on the target host:

[wait_for_connection]: http://docs.ansible.com/ansible/latest/wait_for_connection_module.html

    - hosts: larstest
      gather_facts: false
      tasks:
        - name: wait for server to start
          wait_for_connection:

We need to set `gather_facts: false` here because fact gathering
requires a functioning connection to the target host.

And that's it: a recipe for gently shutting down a remote host,
waiting for the shutdown to complete, then later on spinning it back
up and waiting until subsequent Ansible tasks will work correctly.