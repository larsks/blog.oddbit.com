---
categories: [tech]
aliases: ["/2014/10/06/docker-networking-with-dedicat/"]
title: Docker networking with dedicated network containers
date: "2014-10-06"
tags:
  - docker
  - networking
  - kubernetes
---

The current version of Docker has a very limited set of networking
options:

- `bridge` -- connect a container to the Docker bridge
- `host` -- run the container in the global network namespace
- `container:xxx` -- connect a container to the network namespace of
  another container
- `none` -- do not configure any networking

If you need something more than that, you can use a tool like
[pipework][] to provision additional network interfaces inside the
container, but this leads to a synchronization problem: `pipework` can
only be used after your container is running.  This means that when
starting your container, you must have logic that will wait until the
necessary networking is available before starting your service.

[pipework]: https://github.com/jpetazzo/pipework

The [kubernetes][] project uses a clever solution to this problem:

[kubernetes]: https://github.com/GoogleCloudPlatform/kubernetes

Begin by starting a no-op container -- that is, a container that does
not run any services -- with `--net=none`.  It needs to run
*something*; otherwise it will exit.  The `kubernetes/pause` image
implements an extremely minimal "do nothing but wait" solution.

Once you have this no-op container running, you can set up the
corresponding network namespace to meet your requirements.  For
example, you can create a `veth` device pair and place one end in the
interface and attach another to a bridge on your system.  [Pipework][]
can help with this, but you can also perform all the [changes by
hand][]

[changes by hand]: {{< ref "four-ways-to-connect-a-docker" >}}

Once your networking is configured, start your actual service
container with `--net=container:<id-of-noop-container>`.  Your service
container will start with your configured network environment.

You could, I suppose, decide to link *every* service container with
it's own network container, but that would get messy. Kubernetes
groups containers together into "pods", in which all containers in a
pod share the same network namespace, which reduces the number of
"networking containers" necessary for services that have the same
networking requirements.

This solution -- linking your service container with a no-op container
used to implement networking -- solves the problems identified at the
beginning of this post: because you can perform all your network
configuration prior to starting your service, your service container
does not need any special logic to deal with interfaces that will be
created after the container starts.  The networking will already be
in place when the service starts.

Docker issue [7455] proposes a docker-native solution that would
accomplish largely the same thing without requiring the separate
networking container (by permitting you to pre-configure a network
namespace and then pass that to docker using something like
`--net=netns:<name-of-network-namespace>`).

[7455]: https://github.com/docker/docker/issues/7455

