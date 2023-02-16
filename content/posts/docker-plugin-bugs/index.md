---
categories: [tech]
aliases: ["/2014/09/01/docker-plugin-bugs/"]
title: Docker plugin bugs
date: "2014-09-01"
tags:
- openstack
- docker
- heat
- pull-request
---

This is a companion to my [article on the Docker plugin for Heat][1].

[1]: {{< ref "docker-plugin-for-openstack-he" >}}

While writing that article, I encountered a number of bugs in the
Docker plugin and elsewhere.  I've submitted patches for most of the
issues I encountered:

## Bugs in the Heat plugin

- <https://bugs.launchpad.net/heat/+bug/1364017>

    docker plugin fails to delete a container resource in
  `CREATE_FAILED` state.

- <https://bugs.launchpad.net/heat/+bug/1364041>

    docker plugin `volumes_from` parameter should be a list.

- <https://bugs.launchpad.net/heat/+bug/1364039>

    docker plugin `volumes_from` parameter results in an error

- <https://bugs.launchpad.net/heat/+bug/1364019>

    docker plugin does not actually remove containers on delete

## Bugs in docker Python module

- <https://github.com/docker/docker-py/pull/310>

    allow ports to be specified as `port/proto`.

