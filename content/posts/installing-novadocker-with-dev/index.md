---
aliases:
- /2015/02/11/installing-novadocker-with-devstack/
- /post/2015-02-11-installing-novadocker-with-devstack
categories:
- tech
date: '2015-02-11'
tags:
- openstack
- docker
- devstack
title: Installing nova-docker with devstack
---

This is a long-form response to [this question][ask], and describes
how to get the [nova-docker][] driver up running with [devstack][]
under Ubuntu 14.04 (Trusty).  I wrote a [similar post][] for Fedora
21, although that one was using the [RDO][] Juno packages, while this
one is using [devstack][] and the upstream sources.

[similar post]: {{< ref "installing-nova-docker-on-fedo" >}}
[rdo]: http://openstack.redhat.com/
[ask]: https://ask.openstack.org/en/question/60679/installing-docker-on-openstack-with-ubuntu/
[nova-docker]: http://github.com/stackforge/nova-docker/
[devstack]: http://devstack.org/

## Getting started

We'll be using the [Ubuntu 14.04 cloud image][ubuntu] (because my test
environment runs on [OpenStack][]).

[ubuntu]: https://cloud-images.ubuntu.com/trusty/current/
[openstack]: http://www.openstack.org/

First, let's install a few prerequisites:

    $ sudo apt-get update
    $ sudo apt-get -y install git git-review python-pip python-dev

And generally make sure things are up-to-date:

    $ sudo apt-get -y upgrade

## Installing Docker

We need to install Docker if we're going to use `nova-docker`.

Ubuntu 14.04 includes a fairly dated version of Docker, so I followed
[the instructions][] on the Docker website for installing the current
version of Docker on Ubuntu; this ultimately got me:

    $ sudo apt-get -y install lxc-docker
    $ sudo docker version
    Client version: 1.5.0
    Client API version: 1.17
    Go version (client): go1.4.1
    Git commit (client): a8a31ef
    OS/Arch (client): linux/amd64
    Server version: 1.5.0
    Server API version: 1.17
    Go version (server): go1.4.1
    Git commit (server): a8a31ef

[the instructions]: https://docs.docker.com/installation/ubuntulinux/#docker-maintained-package-installation

Docker by default creates its socket (`/var/run/docker.socket`) with
`root:root` ownership.  We're going to be running devstack as the
`ubuntu` user, so let's change that by editing `/etc/default/docker`
and setting:

    DOCKER_OPTS='-G ubuntu'

And restart `docker`:

    $ sudo restart docker

And verify that we can access Docker as the `ubuntu` user:

    $ docker version
    Client version: 1.5.0
    Client API version: 1.17
    [...]

## Installing nova-docker

As the `ubuntu` user, let's get the `nova-docker` source code:

    $ git clone http://github.com/stackforge/nova-docker.git
    $ cd nova-docker

As of this writing (`HEAD` is "984900a Give some time for docker.stop
to work"), you need to apply [a patch][] to `nova-docker` to get it to
work with the current Nova `master` branch:

[a patch]: https://review.openstack.org/#/c/154750/

    $ git fetch https://review.openstack.org/stackforge/nova-docker \
      refs/changes/50/154750/3 \
      && git checkout FETCH_HEAD

Once [that change][a patch] has merged (**update**, 2015-02-12: the
patch has merged), this step should no longer be
necessary.  With the patch we applied, we can install the
`nova-docker` driver:

    $ sudo pip install .

## Configuring devstack

Now we're ready to get devstack up and running.  Start by cloning the
repository:

    $ git clone https://git.openstack.org/openstack-dev/devstack
    $ cd devstack

Then create a `local.conf` file with the following content:

    [[local|localrc]]
    ADMIN_PASSWORD=secret
    DATABASE_PASSWORD=$ADMIN_PASSWORD
    RABBIT_PASSWORD=$ADMIN_PASSWORD
    SERVICE_PASSWORD=$ADMIN_PASSWORD
    SERVICE_TOKEN=super-secret-admin-token
    VIRT_DRIVER=novadocker.virt.docker.DockerDriver

    DEST=$HOME/stack
    SERVICE_DIR=$DEST/status
    DATA_DIR=$DEST/data
    LOGFILE=$DEST/logs/stack.sh.log
    LOGDIR=$DEST/logs

    # The default fixed range (10.0.0.0/24) conflicted with an address
    # range I was using locally.
    FIXED_RANGE=10.254.1.0/24
    NETWORK_GATEWAY=10.254.1.1

    # This enables Neutron, because that's how I roll.
    disable_service n-net
    enable_service q-svc
    enable_service q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta

    # I am disabling horizon (because I rarely use the web ui)
    # and tempest in order to make the installer complete a 
    # little faster.
    disable_service horizon
    disable_service tempest

    # Introduce glance to docker images
    [[post-config|$GLANCE_API_CONF]]
    [DEFAULT]
    container_formats=ami,ari,aki,bare,ovf,ova,docker

    # Configure nova to use the nova-docker driver
    [[post-config|$NOVA_CONF]]
    [DEFAULT]
    compute_driver=novadocker.virt.docker.DockerDriver

This will result in things getting installed in subdirectories of
`$HOME/stack`.  We enable Neutron and leave pretty much everything
else set to default values.

## Start the installation

So, now we're all ready to roll!

    $ ./stack.sh
    [Call Trace]
    ./stack.sh:151:source
    /home/ubuntu/devstack/stackrc:665:die
    [ERROR] /home/ubuntu/devstack/stackrc:665 Could not determine host ip address. See local.conf for suggestions on setting HOST_IP.
    /home/ubuntu/devstack/functions-common: line 322: /home/ubuntu/stack/logs/error.log: No such file or directory

...or not.  This error happens if devstack is unable to turn your
hostname into an IP address.  We can set `HOST_IP` in our
environment:

    $ HOST_IP=10.0.0.232 ./stack.sh

And then go grab a cup of coffee or something.

## Install nova-docker rootwrap filters

Once `stack.sh` is finished running, we need to install a `rootwrap`
configuration file for `nova-docker`:

    $ sudo cp nova-docker/etc/nova/rootwrap.d/docker.filters \
      /etc/nova/rootwrap.d/

## Starting a Docker container

Now that our environment is up and running, we should be able to start
a container.  We'll start by grabbing some admin credentials for our
OpenStack environment:

    $ . openrc admin

Next, we need an appropriate image; my [larsks/thttpd][] image
is small (so it's quick to download) and does not require any
interactive terminal (so it's appropriate for nova-docker), so let's
start with that:

[larsks/thttpd]: https://registry.hub.docker.com/u/larsks/thttpd/

    $ docker pull larsks/thttpd
    $ docker save larsks/thttpd |
      glance image-create --name larsks/thttpd \
        --is-public true --container-format docker \
        --disk-format raw

And now we'll boot it up.  I like to do this as a non-admin user:

    $ . openrc demo
    $ nova boot --image larsks/thttpd --flavor m1.small test0

After a bit, we should see:

    $ nova list
    +----...+-------+--------+...+-------------+--------------------+
    | ID ...| Name  | Status |...| Power State | Networks           |
    +----...+-------+--------+...+-------------+--------------------+
    | 0c3...| test0 | ACTIVE |...| Running     | private=10.254.1.4 |
    +----...+-------+--------+...+-------------+--------------------+

Let's create a floating ip address:

    $ nova floating-ip-create
    +------------+-----------+----------+--------+
    | Ip         | Server Id | Fixed Ip | Pool   |
    +------------+-----------+----------+--------+
    | 172.24.4.3 | -         | -        | public |
    +------------+-----------+----------+--------+

And assign it to our container:

    $ nova floating-ip-associate test0 172.24.4.3

And now access our service:

    $ curl http://172.24.4.3
    <!DOCTYPE html>
    <html>
            <head>            
                    <title>Your web server is working</title>
    [...]
