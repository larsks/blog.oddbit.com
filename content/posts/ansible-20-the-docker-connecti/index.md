---
aliases:
- /2015/10/13/ansible-20-the-docker-connection-driver/
- /post/2015-10-13-ansible-20-the-docker-connection-driver
categories:
- tech
date: '2015-10-13'
tags:
- ansible
- docker
- ansible_20_series
title: 'Ansible 2.0: The Docker connection driver'
---

As the release of [Ansible][] 2.0 draws closer, I'd like to take a
look at some of the new features that are coming down the pipe.  In
this post, we'll look at the `docker` connection driver.

[ansible]: http://ansible.com/

A "connection driver" is the mechanism by which Ansible connects to
your target hosts.  These days it uses `ssh` by default (which relies
on the OpenSSH command line client for connectivity), and it also
offers the [Paramiko][] library as an alternative ssh implementation
(this was in fact the default driver in earlier versions of Ansible).
Alternative drivers offered by recent versions of ansible included the
`winrm` driver, for accessing Windows hosts, the `fireball` driver, a
(deprecated) driver that used [0mq][] for communication, and `jail`, a
driver for connecting to FreeBSD jails.

[paramiko]: http://www.paramiko.org/
[0mq]: http://zeromq.org/

Ansible 2.0 will offer a `docker` connection driver, which can be used
to connect to Docker containers via the `docker exec` command.
Assuming you have a running container named `target`, you can run an
ad-hoc command like this:

    $ ansible all -i target, -c docker -m command -a 'uptime'
    target | SUCCESS | rc=0 >>
     03:54:21 up 7 days, 15:00,  0 users,  load average: 0.81, 0.60, 0.46

You can specify the connection driver as part of a play in your
playbook:

    - hosts: target
      connection: docker
      tasks:
        - package:
            name: git
            state: latest

Or as a variable in your inventory.  Here's an example that has both a
docker container and an ssh-accessible host:

    target ansible_connection=docker
    server ansible_host=192.168.1.20 ansible_user=root

Given the following playbook:

    - hosts: all
      tasks:
        - ping:

If we run it like this, assuming the above inventory is in the file
`inventory`:

    $ ansible-playbook -i inventory playbook.yml

The output will look something like:

    TASK [ping] ********************************************************************
    <192.168.1.20> ESTABLISH SSH CONNECTION FOR USER: root
    <192.168.1.20> SSH: EXEC ssh -C -q -o ControlMaster=auto -o ControlPersist=60s ... 192.168.1.20 ...
    <192.168.1.20> PUT /tmp/tmpbtrmo5 TO /root/.ansible/tmp/ansible-tmp-1444795190.49-64658551273604/ping
    <192.168.1.20> SSH: EXEC sftp -b - -C -o ControlMaster=auto -o ControlPersist=60s ... 192.168.1.20 ...
    ESTABLISH DOCKER CONNECTION FOR USER: lars
    <target> EXEC ['/usr/bin/docker', 'exec', '-i', u'target', '/bin/sh', '-c', ...
    <target> PUT /tmp/tmpNmcPTf TO /root/.ansible/tmp/ansible-tmp-1444795190.53-251446545325875/ping
    <192.168.1.20> ESTABLISH SSH CONNECTION FOR USER: root
    <192.168.1.20> SSH: EXEC ssh -C -q -o ControlMaster=auto -o ControlPersist=60s ... 192.168.1.20 ...
    ok: [server -> localhost] => {"changed": false, "ping": "pong"}
    <target> EXEC ['/usr/bin/docker', 'exec', '-i', u'target', '/bin/sh', '-c', ...
    ok: [target -> localhost] => {"changed": false, "ping": "pong"}

    PLAY RECAP *********************************************************************
    server                     : ok=2    changed=0    unreachable=0    failed=0   
    target                     : ok=2    changed=0    unreachable=0    failed=0   

Now you have a unified mechanism for managing configuration changes in
traditional hosts as well as in Docker containers.