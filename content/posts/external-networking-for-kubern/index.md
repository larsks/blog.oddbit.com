---
aliases:
- /2015/02/10/external-networking-for-kubernetes-services/
- /post/2015-02-10-external-networking-for-kubernetes-services
categories:
- tech
date: '2015-02-10'
tags:
- docker
- kubernetes
title: External networking for Kubernetes services
---

I have recently started running some "real" services (that is,
"services being consumed by someone other than myself") on top of
Kubernetes (running on bare metal), which means I suddenly had to
confront the question of how to provide external access to Kubernetes
hosted services.  Kubernetes provides two solutions to this problem,
neither of which is particularly attractive out of the box:

1. There is a field `createExternalLoadBalancer` that can be set in a
   service description.  This is meant to integrate with load
   balancers provided by your local cloud environment, but at the
   moment there is only support for this when running under [GCE][].

1. A service description can have a list of public IP addresses
   associated with it in the `publicIPS` field.  This will cause
   `kube-proxy` to create rules in the `KUBE-PROXY` chain of your
   `nat` table to direct traffic inbound to those addresses to the
   appropriate local `kube-proxy` port.

The second option is a good starting point, since if you were to
simply list the public IP addresses of your Kubernetes minions in the
`publicIPs` field, everything would Just Work.  That is, inbound
traffic to the appropriate port on your minions would get directed to
`kube-proxy` by the `nat` rules.  That's great for simple cases, but
in practice it means that you cannot have more that *N* services
exposed on a given port where *N* is the number of minions in your
cluster.  That limit is difficult if you -- like I do -- have an
all-in-one (e.g., on a single host) Kubernetes deployment on which you
wish to host multiple web services exposed on port 80 (and even in a
larger environment, you really don't want "number of things on port
XX" tightly coupled to "number of minions").

## Introducing Kiwi

To overcome this problem, I wrote [Kiwi][], a service that listens to
Kubernetes for events concerning new/modified/deleted services, and in
response to those events manages (a) the assignment of IP addresses to
network interfaces on your minions and (b) creating additional
firewall rules to permit traffic inbound to your services to pass a
default-deny firewall configuration.

Kiwi uses [etcd][] to coordinate ownership of IP addresses between
minions in your Kubernetes cluster.

## How it works

Kiwi listens to event streams from both Kubernetes and Etcd.

On the Kubernetes side, Kiwi listens to `/api/v1beta/watch/services`,
which produces events in response to new, modified, or deleted
services.  The Kubernetes API uses a server-push model, in which a
client makes a single HTTP request and then receives a series of
events over the same connection.  A event looks something like:

    {
      "type": "ADDED",
      "object": {
        "portalIP": "10.254.93.176",
        "containerPort": 80,
        "publicIPs": [
          "192.168.1.100"
        ],
        "selector": {
          "name": "test-web"
        },
        "protocol": "TCP",
        "port": 8080,
        "kind": "Service",
        "id": "test-web",
        "uid": "72bc1286-a440-11e4-b83e-20cf30467e62",
        "creationTimestamp": "2015-01-24T22:15:43-05:00",
        "selfLink": "/api/v1beta1/services/test-web",
        "resourceVersion": 245,
        "apiVersion": "v1beta1",
        "namespace": "default"
      }
    }

I am using the Python [requests][] library, which it turns out [has a
bug][gh#2433] in its handling of streaming server responses, but I was
able to work around that issue once I realized what was going on.

[gh#2433]: https://github.com/kennethreitz/requests/issues/2433
[requests]: http://docs.python-requests.org/en/latest/

On the Etcd side, Kiwi uses keys under the `/kiwi/publicips` prefix to
coordinate address ownership among Kiwi instances.  It listens to
events from Etcd regarding key create/delete/set/etc operations in
this prefix by calling
`/v2/keys/kiwi/publicips?watch=true&recursive=true`.  This is a
long-poll request, rather than a streaming request: that means that a
request will only ever receive a single event, but it may need to wait
for a while before it receives that response.  This model worked well
with the `requests` library out of the box.

After receiving an event from Kubernetes, Kiwi iterates over the
public IP addresses in the `publicIPs` key, and for any address that
is not already being manged by the local instance it makes a claim on
that address by attempting to atomically create a key in etcd under
`/kiwi/publicips/` (such as `/kiwi/publicips/192.168.1.100`).  If this
attempt succeeds, Kiwi on the local minion has claimed that address
and proceeds to assign it to the local interface.  If the attempt to
set that key does not succeed, it means the address is already being
managed by Kiwi on another minion.

The address keys are set with a TTL of 20 seconds, after which they
will be expired.  If an address expires, other Kiwi instances will
receive notification from Etcd and ownership of that address will
transfer to another Kiwi instance.

## Getting started with Kiwi

The easiest way to get started with Kiwi is to use the [larsks/kiwi][]
Docker image that is automatically built from the [Git
repository][kiwi].  For example, if you want to host public ip
addresses on `eth0` in the range `192.168.1.32/28`, you would start it
like this:

[larsks/kiwi]: https://registry.hub.docker.com/u/larsks/kiwi/

    docker run --privileged --net=host larsks/kiwi \
      --interface eth0 \
      --range 192.168.1.32/28

You need both `--privileged` and `--net=host` in order for Kiwi to
assign addresses to your host interfaces and to manage the iptables
configuration.

## An Example

Start Kiwi as described above.  Next, plae the following content in a
file called `service.yaml`:

    kind: Service
    apiVersion: v1beta1
    id: test-web
    port: 8888
    selector:
      name: test-web
    containerPort: 80
    publicIPs:
      - 192.168.1.100

Create the service using `kubectl`:

    kubectl create -f service.yaml

After a short pause, you should see the address show up on interface
`eth0`; the entry will look something like:

    inet 192.168.1.100/32 scope global dynamic eth0:kube
           valid_lft 17sec preferred_lft 17sec

The `eth0:kube` is a label applied to the address; this allows Kiwi to
clean up these addresses at startup (by getting a list of
Kiwi-configured addresses with `ip addr show label eth0:kube`).

The `valid_lft` and `preferred_lft` fields control the lifetime of the
interface.  When these counters reach 0, the addresses are removed by
the kernel.  This ensure that if Kiwi dies, the addresses can
successfully be re-assigned on another node.

[gce]: https://cloud.google.com/compute/
[kubernetes]: https://github.com/googlecloudplatform/kubernetes
[kiwi]: http://github.com/larsks/kiwi/
[portal]: https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/services.md#ips-and-portals
[etcd]: https://github.com/coreos/etcd