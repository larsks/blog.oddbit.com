---
categories: [tech]
aliases: ["/2012/11/27/avahi-service-discovery/"]
title: Service discovery in the cloud using Avahi
date: "2012-11-27"
---

I'm been writing [a provisioning tool][drifter] for OpenStack
recently, and I've put together a demo configuration that installs a
simple cluster consisting of three backend nodes and a front-end http
proxy.  I needed a way for the backend servers to discover the ip
address of the frontend server.  Since in my target environment
everything would be on the same layer-2 network segment, service
discovery with multicast DNS (mDNS) seemed like the way to go.

[Avahi][] is the canonical mDNS implementation for Linux, and it comes
with command-line tools for interacting with the Avahi server.  There
is also a DBUS interface and appropriate Python bindings for taking
advantage of it.

[Avahi]: http://avahi.org/

It is relatively simple to publish a service with Avahi; you can
simply drop an XML file into `/etc/avahi/services` and you're done.
Discovering services on the client is a little bit more complicated.
Doing it right would involve a chunk of code that interacts with DBUS
in an event-driven environment with lots of callbacks.  It seemed like
a big hammer for my little problem, so I ended up parsing the output
of `avahi-browse` instead.  This turns out to be a little tricker than
you might think, since:

- The master node might come up *after* the backend nodes, so we need
  to wait for it to publish the service registration.
- The registration process on the backends might run before the local
  `avahi-daemon` has started.

The `-p` flag to `avahi-browse` produces parsable output, like this:

    $ avahi-browse -p _http._tcp
    +;eth0;IPv4;master-cluster-lars;Web Site;local

The `-r` flag performs name->address resolution:

    $ avahi-browse -rp _http._tcp
    +;eth0;IPv4;master-cluster-lars;Web Site;local
    =;eth0;IPv4;master-cluster-lars;Web Site;local;master.local;172.16.10.56;80;

The `-t` flag asks `avahi-browse` to terminate after receiving "all"
entries, and `-f` causes `avahi-browse` to retry a connection to
`avahi-daemon` rather than failing if the daemon is not available. Pu
tall together, we get:

    $ avahi-browse -rptf _http._tcp

We can use `awk` to get the information we need, and `timeout` from
GNU coreutils to take care of the situation I encountered in which
`avahi-browse` would never exit.

The final solution look something like this:

    master_name="master-cluster-lars"

    while ! [ "$master_ip" ] ; do
      master_ip=$(timeout 5 avahi-browse -rptf _http._tcp |
        awk -F';' -vmaster_name="$master_name" '
          $1 == "=" && $4 == master_name {print $8}
        ')
    done

The value of `$master_ip` is then used to `POST` a notification to the
master server with `curl`:

    curl --silent -X POST \
             "http://$master_ip/proxy/backend/$(facter macaddress)"


The master service is running [dynproxy][], which is responsible for
maintaining a list of backend servers that can be queried by other
tools (such as Apache).

[drifter]: http://github.com/larsks/drifter
[dynproxy]: http://github.com/larsks/dynproxy-http

