---
aliases:
- /2015/01/17/running-novalibvirt-and-novadocker-on-the-same-host/
- /post/2015-01-17-running-novalibvirt-and-novadocker-on-the-same-host
categories:
- tech
date: '2015-01-17'
tags:
- openstack
- docker
title: Running nova-libvirt and nova-docker on the same host
---

I regularly use [OpenStack][] on my laptop with [libvirt][] as my
hypervisor.  I was interested in experimenting with recent versions of
the [nova-docker][] driver, but I didn't have a spare system available
on which to run the driver, and I use my regular `nova-compute` service
often enough that I didn't want to simply disable it temporarily in
favor of `nova-docker`.

[openstack]: http://www.openstack.org/
[libvirt]: http://www.libvirt.org/
[nova-docker]: https://github.com/stackforge/nova-docker

---

**NB** As pointed out by *gustavo* in the comments, running two
`neutron-openvswitch-agents` on the same host -- as suggested in this
article -- is going to lead to nothing but sadness and doom.  So
kids, don't try this at home.  I'm leaving the article here because I
think it still has some interesting bits.

---

I guess the simplest solution would be to spin up a vm on which to run
`nova-docker`, but why use a simple solution when there are things to
be learned?  I wanted to know if it were possible (and if so, how) to
run both hypervisors on the same physical host.

The naive solution would be to start up another instance of
`nova-compute` configured to use the Docker driver.  Unfortunately,
Nova only permits a single service instance per "host", so starting up
the second instance of `nova-compute` would effectively "mask" the
original one.

Fortunately, Nova's definition of what constitutes a "host" is
somewhat flexible.  Nova supports a `host` configuration key in
`nova.conf` that will cause Nova to identify the host on which it is
running using your explicitly configured value, rather than your
system hostname.  We can take advantage of this to get a second
`nova-compute` instance running on the same system.

## Install nova-docker

We'll start by installing the `nova-docker` driver from
<https://github.com/stackforge/nova-docker>.  If you're running the
Juno release of OpenStack (which I am), you're going to want to use
the `stable/juno` branch of the `nova-docker` repository.  So:

    $ git clone https://github.com/stackforge/nova-docker
    $ cd nova-docker
    $ git checkout stable/juno
    $ sudo python setup.py install

You'll want to read the project's [README][] for complete installation
instructions.

[README]: https://github.com/stackforge/nova-docker/blob/master/README.rst

## Configure nova-docker

Now, rather than configuring `/etc/nova/nova.conf`, we're going to
create a new configuration file, `/etc/nova/nova-docker.conf`, with
only the configuration keys that differ from our primary Nova
configuration:

    [DEFAULT]
    host=nova-docker
    compute_driver=novadocker.virt.docker.DockerDriver
    log_file=/var/log/nova/nova-docker.log
    state_path=/var/lib/nova-docker

You can see that we've set the value of `host` to `nova-docker`, to
differentiate this `nova-compute` service from the `libvirt`-backed
one that is already running.  We've provided the service with a
dedicated log file and state directory to prevent conflicts with the
already-running `nova-compute` service.

To use this configuration file, we'll launch a new instance of the
`nova-compute` service pointing at both the original configuration
file, `/etc/nova/nova.conf`, as well as this `nova-docker`
configuration file.  The command line would look something like:

    nova-compute --config-file /etc/nova/nova.conf \
      --config-file /etc/nova/nova-docker.conf

The ordering of configuration files on the command line is
significant:  later configuration files will override values from
earlier files.

I'm running [Fedora][] 21 on my laptop, which uses [systemd][], so I
created a modified version of the `openstack-nova-compute.service`
unit on my system, and saved it as
`/etc/systemd/system/openstack-nova-docker.service`:

[fedora]: http://www.fedora.org/
[systemd]: http://www.freedesktop.org/wiki/Software/systemd/

    [Unit]
    Description=OpenStack Nova Compute Server (Docker)
    After=syslog.target network.target

    [Service]
    Environment=LIBGUESTFS_ATTACH_METHOD=appliance
    Type=notify
    Restart=always
    User=nova
    ExecStart=/usr/bin/nova-compute --config-file /etc/nova/nova.conf --config-file /etc/nova/nova-docker.conf

    [Install]
    WantedBy=multi-user.target

And then activated the service;

    # systemctl enable openstack-nova-docker
    # systemctl start openstack-nova-docker

Now, if I run `nova service-list` with administrator credentials, I
can see both `nova-compute` instances:

    +----+------------------+------------------+----------+---------+-------...
    | Id | Binary           | Host             | Zone     | Status  | State ...
    +----+------------------+------------------+----------+---------+-------...
    | 1  | nova-consoleauth | host.example.com | internal | enabled | up    ...
    | 2  | nova-scheduler   | host.example.com | internal | enabled | up    ...
    | 3  | nova-conductor   | host.example.com | internal | enabled | up    ...
    | 5  | nova-cert        | host.example.com | internal | enabled | up    ...
    | 6  | nova-compute     | host.example.com | nova     | enabled | up    ...
    | 7  | nova-compute     | nova-docker      | nova     | enabled | up    ...
    +----+------------------+------------------+----------+---------+-------...

## Booting a Docker container (take 1)

Let's try starting a Docker container using the new `nova-compute`
service.  We'll first need to load a Docker image into Glance (you
followed the `nova-docker` [instructions for configuring
Glance][glance], right?).  We'll use my [larsks/thttpd][] image,
because it's very small and doesn't require any configuration:

[larsks/thttpd]: https://registry.hub.docker.com/u/larsks/thttpd/
[glance]: https://github.com/stackforge/nova-docker#1-enable-the-driver-in-glances-configuration

    $ docker pull larsks/thttpd
    $ docker save larsks/thttpd |
      glance image-create --is-public True --container-format docker \
        --disk-format raw --name larsks/thttpd

(Note that you will probably require administrative credentials to load
this image into Glance.)

Now that we have an appropriate image available we can try booting a container:

    $ nova boot --image larsks/thttpd --flavor m1.small test1

If we wait a moment and then run `nova list`, we see:

    | 9a783952-a888-4fcd-8f5d-cd9291ed1969 | test1   | ERROR  | spawning   ...

[What happened?][]  Looking at the appropriate log file
(`/var/log/nova/nova-docker.log`), we find:

[what happened?]: http://www.sadtrombone.com/

    Cannot setup network: Unexpected vif_type=binding_failed
    Traceback (most recent call last):
      File "/usr/lib/python2.7/site-packages/novadocker/virt/docker/driver.py", line 367, in _start_container
        self.plug_vifs(instance, network_info)
      File "/usr/lib/python2.7/site-packages/novadocker/virt/docker/driver.py", line 187, in plug_vifs
        self.vif_driver.plug(instance, vif)
      File "/usr/lib/python2.7/site-packages/novadocker/virt/docker/vifs.py", line 63, in plug
        _("Unexpected vif_type=%s") % vif_type)
    NovaException: Unexpected vif_type=binding_failed

The message `vif_type=binding_failed` is Nova's way of saying "I have
no idea what happened, go ask Neutron".  Looking in Neutron's
`/var/log/neutron/server.log`, we find:

    Failed to bind port 82c07caa-b2c2-45e9-955d-e8b35112437c on host
    nova-docker
    
And this tells us our problem: we have told our `nova-docker` service
that it is running on a host called "nova-docker", and Neutron doesn't
know anything about that host.

---

**NB**

If you were to try to delete this failed instance, you would find that
it is un-deletable.  In the end, I was only able to delete it by
directly editing the `nova` database using [this sql script][].

[this sql script]: delete-deleting-instances.sql

---

## Adding a Neutron agent

We're going to need to set up an instance of
`neutron-openvswitch-agent` to service network requests on our
"nova-docker" host.  Like Nova, Neutron also supports a `host`
configuration key, so we're going to pursue a solution similar to what
we used with Nova by creating a new configuration file,
`/etc/neutron/ovs-docker.conf`, with the following content:

    [DEFAULT]
    host = nova-docker

And then we'll set up the corresponding service by dropping the
following into `/etc/systemd/system/docker-openvswitch-agent.service`:

    [Unit]
    Description=OpenStack Neutron Open vSwitch Agent (Docker)
    After=syslog.target network.target

    [Service]
    Type=simple
    User=neutron
    ExecStart=/usr/bin/neutron-openvswitch-agent --config-file /usr/share/neutron/neutron-dist.conf --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/openvswitch/ovs_neutron_plugin.ini --config-file /etc/neutron/ovs-docker.conf --log-file /var/log/neutron/docker-openvswitch-agent.log
    PrivateTmp=true
    KillMode=process

    [Install]
    WantedBy=multi-user.target

----

**NB**

While working on this configuration I ran into an undesirable
interaction between Docker and [systemd][]'s `PrivateTmp` directive.

This directive causes the service to run with
a private [mount namespace][] such that `/tmp` for the service is not
the same as `/tmp` for other services.  This is a great idea from a
security perspective, but can cause problems in the following
scenario:

1. Start a Docker container with `nova boot ...`
2. Restart any service that uses the `PrivateTmp` directive
3. Attempt to delete the Docker container with `nova delete ...`

Docker will fail to destroy the container because the private
namespace created by the `PrivateTmp` directive preserves a reference
to the Docker `devicemapper` mount in
`/var/lib/docker/devicemapper/mnt/...` that was active at the time the
service was restarted.  To recover from this situation, you will need
to restart whichever service is still holding a reference to the
Docker mounts.

I have [posted to the systemd-devel][docker-vs-privatetmp] mailing
list to see if there are any solutions to this behavior.  As I note in
that email, this behavior appears to be identical to that described in
Fedora bug [851970][], which was closed two years ago.

[mount namespace]: http://lwn.net/Articles/531114/
[docker-vs-privatetmp]: http://lists.freedesktop.org/archives/systemd-devel/2015-January/027162.html
[851970]: https://bugzilla.redhat.com/show_bug.cgi?id=851970

**Update** I wrote a [separate post][] about this issue, which
includes some discussion about what's going on and a solution.

[separate post]: {{< ref "docker-vs-privatetmp" >}}

----

If we activate this service...

    # systemctl enable docker-openvswitch-agent
    # systemctl start docker-openvswitch-agent

...and then run `neutron agent-list` with administrative credentials,
we'll see the new agent:

    $ neutron agent-list
    +--------------------------------------+--------------------+------------------+-------+...
    | id                                   | agent_type         | host             | alive |...
    +--------------------------------------+--------------------+------------------+-------+...
    | 2e40062a-1c30-46a3-8719-3ce93a56b4ce | Open vSwitch agent | nova-docker      | :-)   |...
    | 63edb2a4-f980-4f88-b9c0-9610a1b20f13 | L3 agent           | host.example.com | :-)   |...
    | 8482c5c3-208c-4145-9f7d-606be3da11ed | Loadbalancer agent | host.example.com | :-)   |...
    | 9922ed54-00fa-41d4-96e8-ac8af8c291fd | Open vSwitch agent | host.example.com | :-)   |...
    | b8becb9c-7290-42be-9faf-fd3baeea3dcf | Metadata agent     | host.example.com | :-)   |...
    | c46be41b-e93a-40ab-a37e-4d67b770a3df | DHCP agent         | host.example.com | :-)   |...
    +--------------------------------------+--------------------+------------------+-------+...

## Booting a Docker container (take 2)

Now that we have both the `nova-docker` service running and a
corresponding `neutron-openvswitch-agent` available, let's try
starting our container one more time:

    $ nova boot --image larsks/thttpd --flavor m1.small test1
    $ nova list
    +--------------------------------------+---------+--------+...
    | ID                                   | Name    | Status |...
    +--------------------------------------+---------+--------+...
    | 642b7d61-9189-40ea-86f5-2424c3c86028 | test1   | ACTIVE |...
    +--------------------------------------+---------+--------+...

If we assign a floating IP address:

    $ nova floating-ip-create ext-nat
    +-----------------+-----------+----------+---------+
    | Ip              | Server Id | Fixed Ip | Pool    |
    +-----------------+-----------+----------+---------+
    | 192.168.200.211 | -         | -        | ext-nat |
    +-----------------+-----------+----------+---------+
    $ nova floating-ip-associate test1 192.168.200.211

We can then browse to `http://192.168.200.211` and see the sample
page:

    $ curl http://192.168.200.211/
    .
    .
    .
      ____                            _         _       _   _                 
     / ___|___  _ __   __ _ _ __ __ _| |_ _   _| | __ _| |_(_) ___  _ __  ___ 
    | |   / _ \| '_ \ / _` | '__/ _` | __| | | | |/ _` | __| |/ _ \| '_ \/ __|
    | |__| (_) | | | | (_| | | | (_| | |_| |_| | | (_| | |_| | (_) | | | \__ \
     \____\___/|_| |_|\__, |_|  \__,_|\__|\__,_|_|\__,_|\__|_|\___/|_| |_|___/
                      |___/                                                   
    .
    .
    .

## Booting a libvirt instance

To show that we really are running two hypervisors on the same host,
we can launch a traditional `libvirt` instance alongside our Docker
container:

    $ nova boot --image cirros --flavor m1.small --key-name lars test2

Wait a bit, then:

    $ nova list
    +--------------------------------------+-------+--------+...
    | ID                                   | Name  | Status |...
    +--------------------------------------+-------+--------+...
    | 642b7d61-9189-40ea-86f5-2424c3c86028 | test1 | ACTIVE |...
    | 7fec33c9-d50f-477e-957c-a05ee9bd0b0b | test2 | ACTIVE |...
    +--------------------------------------+-------+--------+...
