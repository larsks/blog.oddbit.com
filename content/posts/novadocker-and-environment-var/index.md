---
categories: [tech]
aliases: ["/2014/08/28/novadocker-and-environment-var/"]
title: nova-docker and environment variables
date: "2014-08-28"
tags:
  - openstack
  - docker
---

I've been playing with [Docker][] a bit recently, and decided to take
a look at the [nova-docker][] driver for [OpenStack][].

[docker]: https://docker.com/
[nova-docker]: https://github.com/stackforge/nova-docker
[openstack]: http://openstack.org/

The `nova-docker` driver lets Nova, the OpenStack Compute service,
spawn Docker containers instead of hypervisor-based servers.  For
certain workloads, this leads to better resource utilization than you
would get with a hypervisor-based solution, while at the same time
givin you better support for multi-tenancy and flexible networking
than you get with Docker by itself.

The [Docker driver wiki][wiki] was mostly sufficient for getting the
`nova-docker` driver installed in my existing OpenStack deployment,
although I did make a few [small changes][] to the wiki to reflect
some missing steps.  Other than that, the installation was relatively
simple and I was soon able to spin up Docker containers using `nova
boot ...` 

[wiki]: https://wiki.openstack.org/wiki/Docker
[small changes]: https://wiki.openstack.org/w/index.php?title=Docker&diff=61664&oldid=58546

The one problem I encountered is that it is not possible to pass
environment variable to Docker containers via the `nova-docker`
driver.  Many existing images (such as the [official MySQL image][])
expect configuration information to be passed in using environment
variables; for example, the `mysql` image expects to be started like
this:

    docker run --name some-mysql \
      -e MYSQL_ROOT_PASSWORD=mysecretpassword -d mysql

I have proposed a [patch][] to the `nova-docker` driver that permits
one to provide environment variables via the Nova metadata service.
With this patch in place, I would start the `mysql` container like
this:

    nova boot --image mysql --flavor m1.small \
      --meta ENV_MYSQL_ROOT_PASSWORD=mysecretpassword \
      some-mysql

That is, the driver looks for metadata items that begin with `ENV_`
and transforms these into Docker environment variables after stripping
`ENV_` from the name.

[patch]: https://review.openstack.org/#/c/117583/
[official mysql image]: https://registry.hub.docker.com/_/mysql/

While this patch works great in my testing environment, it's unlikely
to get accepted.  Generally, the metadata provided by Nova belongs to
the tenant and is not meant to be operationally significant to the
compute driver itself.

It sounds as if there is a lot of work going on right now regarding
container support in OpenStack, so it is very likely that a better
solution will show up in the near future.

In the absence of that support, I hope others find this patch helpful.

