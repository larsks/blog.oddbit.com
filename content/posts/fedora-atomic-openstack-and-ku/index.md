---
aliases:
- /2014/11/24/fedora-atomic-openstack-and-kubernetes-oh-my/
- /post/2014-11-24-fedora-atomic-openstack-and-kubernetes-oh-my
categories:
- tech
date: '2014-11-24'
tags:
- openstack
- kubernetes
- fedora
- atomic
title: Fedora Atomic, OpenStack, and Kubernetes (oh my)
---

While experimenting with [Fedora Atomic][], I was looking for an
elegant way to automatically deploy Atomic into an [OpenStack][]
environment and then automatically schedule some [Docker][] containers
on the Atomic host.  This post describes my solution.

[fedora atomic]: http://www.projectatomic.io/
[docker]: http://docker.com/
[openstack]: http://openstack.org/

<!-- more -->

Like many other cloud-targeted distributions, Fedora Atomic runs
[cloud-init][] when the system boots.  We can take advantage of this
to configure the system at first boot by providing a `user-data` blob
to Nova when we boot the instance.  A `user-data` blob can be as
simple as a shell script, and while we could arguably mash everything
into a single script it wouldn't be particularly maintainable or
flexible in the face of different pod/service/etc descriptions.

[cloud-init]: http://cloudinit.readthedocs.org/

In order to build a more flexible solution, we're going to take
advantage of the following features:

- Support for [multipart MIME archives][ci-multipart].

    Cloud-init allows you to pass in multiple files via `user-data` by
    encoding them as a multipart MIME archive.

- Support for a [custom part handler][ci-part].

    Cloud-init recognizes a number of specific MIME types (such as
    `text/cloud-config` or `text/x-shellscript`).  We can provide a
    custom part handler that will be used to handle MIME types not
    intrinsincally supported by `cloud-init`.

[ci-multipart]: http://cloudinit.readthedocs.org/en/latest/topics/format.html#mime-multi-part-archive
[ci-part]: http://cloudinit.readthedocs.org/en/latest/topics/format.html#part-handler

## A custom part handler for Kubernetes configurations

I have written a [custom part handler][kube-part-handler] that knows
about the following MIME types:

[kube-part-handler]: https://github.com/larsks/atomic-kubernetes-tools/blob/master/kube-part-handler.py

- `text/x-kube-pod`
- `text/x-kube-service`
- `text/x-kube-replica`

When the part handler is first initialized it will ensure the
Kubernetes is started.  If it is provided with a document matching one
of the above MIME types, it will pass it to the appropriate `kubecfg`
command to create the objects in Kubernetes.

## Creating multipart MIME archives

I have also created a [modified version][] of the standard
`write-multipart-mime.py` Python script.  This script will inspect the
first lines of files to determine their content type; in addition to
the standard `cloud-init` types (like `#cloud-config` for a
`text/cloud-config` type file), this script recognizes:

[modified version]: https://github.com/larsks/atomic-kubernetes-tools/blob/master/write-mime-multipart.py

- `#kube-pod` for `text/x-kube-pod`
- `#kube-service` for `text/x-kube-service`
- `#kube-replica` for `text/x-kube-replca`

That is, a simple pod description might look something like:

    #kube-pod
    id: dbserver
    desiredState:
      manifest:
        version: v1beta1
        id: dbserver
        containers:
        - image: mysql
          name: dbserver
          env:
            - name: MYSQL_ROOT_PASSWORD
              value: secret

## Putting it all together

Assuming that the pod description presented in the previous section is
stored in a file named `dbserver.yaml`, we can bundle that file up
with our custom part handler like this:

    $ write-mime-multipart.py \
      kube-part-handler.py dbserver.yaml > userdata

We would then launch a Nova instance using the `nova boot` command,
providing the generated `userdata` file as an argument to the
`user-data` command:

    $ nova boot --image fedora-atomic --key-name mykey \
      --flavor m1.small --user-data userdata my-atomic-server

You would obviously need to substitute values for `--image` and
`--key-name` that are appropriate for your environment.

## Details, details

If you are experimenting with Fedora Atomic 21, you may find out that
the above example doesn't work -- the official `mysql` image generates
an selinux error.  We can switch selinux to permissive mode by putting
the following into a file called `disable-selinux.sh`:

    #!/bin/sh

    setenforce 0
    sed -i '/^SELINUX=/ s/=.*/=permissive/' /etc/selinux/config

And then including that in our MIME archive:

    $ write-mime-multipart.py \
      kube-part-handler.py disable-selinux.sh dbserver.yaml > userdata

## A brief demonstration

If we launch an instance as described in the previous section and then
log in, we should find that the pod has already been scheduled:

    # kubecfg list pods
    ID                  Image(s)            Host                Labels              Status
    ----------          ----------          ----------          ----------          ----------
    dbserver            mysql               /                                       Waiting

At this point, `docker` needs to pull the `mysql` image locally, so
this step can take a bit depending on the state of your local internet
connection.

Running `docker ps` at this point will yield:

    # docker ps
    CONTAINER ID        IMAGE                     COMMAND             CREATED             STATUS              PORTS               NAMES
    3561e39f198c        kubernetes/pause:latest   "/pause"            46 seconds ago      Up 43 seconds                           k8s--net.d96a64a9--dbserver.etcd--3d30eac0_-_745c_-_11e4_-_b32a_-_fa163e6e92ce--d872be51   

The `pause` image here is a Kubernetes detail that is used to
configure the networking for a pod (in the Kubernetes world, a pod is
a group of linked containers that share a common network namespace).

After a few minutes, you should eventually see:

    # docker ps
    CONTAINER ID        IMAGE                     COMMAND                CREATED             STATUS              PORTS               NAMES
    644c8fc5a79c        mysql:latest              "/entrypoint.sh mysq   3 minutes ago       Up 3 minutes                            k8s--dbserver.fd48803d--dbserver.etcd--3d30eac0_-_745c_-_11e4_-_b32a_-_fa163e6e92ce--58794467   
    3561e39f198c        kubernetes/pause:latest   "/pause"               5 minutes ago       Up 5 minutes                            k8s--net.d96a64a9--dbserver.etcd--3d30eac0_-_745c_-_11e4_-_b32a_-_fa163e6e92ce--d872be51        

And `kubecfg` should show the pod as running:

    # kubecfg list pods
    ID                  Image(s)            Host                Labels              Status
    ----------          ----------          ----------          ----------          ----------
    dbserver            mysql               127.0.0.1/                              Running


## Problems, problems

This works and is I think a relatively elegant solution.  However,
there are some drawbacks.  In particular, the custom part handler
runs fairly early in the `cloud-init` process, which means that it
cannot depend on changes implemented by `user-data` scripts (because
these run much later).

A better solution might be to have the custom part handler simply
write the Kubernetes configs into a directory somewhere, and then
install a service that launches after Kubernetes and (a) watches that
directory for files, then (b) passes the configuration to Kubernetes
and deletes (or relocates) the file.