---
categories: [tech]
aliases: ["/2014/10/22/building-docker-images-with-pu/"]
title: Building Docker images with Puppet
date: "2014-10-22"
tags:
  - puppet
  - docker
---

I like [Docker][], but I'm not a huge fan of using shell scripts for
complex system configuration...and Dockerfiles are basically giant
shell scripts.

[docker]: http://docker.com/

I was curious whether or not it would be possible to use Puppet during
the `docker build` process.  As a test case, I used the
[ssh][] module included in the openstack-puppet-modules package.

[ssh]: https://github.com/saz/puppet-ssh

I started with a manifest like this (in `puppet/node.pp`):

    class { 'ssh': }

And a Dockerfile like this:

    FROM larsks/rdo-puppet-base

    COPY puppet /puppet
    RUN cd /puppet; puppet apply \
      --modulepath /usr/share/openstack-puppet/modules \
      node.pp

The `larsks/rdo-puppet-base` module includes "puppet" and all the Puppet
modules required by RDO (installed in
`/usr/share/openstack-puppet/modules`).

Running `docker build` with this `Dockerfile` results in:

    Error: Could not run: Could not retrieve facts for
    a9cde05eb735.example.com: no address for
    a9cde05eb735.example.com

Puppet is trying to determine the FQDN of the container, and is then
trying to determine the canonical ip address of the container.  This is
never going to work, absent some mechanism that automatically
registers DNS entries when you boot containers (e.g., [skydock][]).

[skydock]: https://github.com/crosbymichael/skydock

The obvious way to fix this would be to modify `/etc/hosts` and add
the calculated fqdn to the entry for `localhost`, but `/etc/hosts`
inside Docker containers is read-only.

Since Puppet is using Facter to get information about the host, I
looked into whether or not it would be possible (and convenient) to
override Facter generated facts.  It turns out that it [is relatively
easy][override]; just set `FACTER_<fact_name>` in the environment.
For example:

[override]: http://www.puppetcookbook.com/posts/override-a-facter-fact.html

    FACTER_fqdn=localhost

I modified the Dockerfile to look like this:

    FROM larsks/rdo-puppet-base

    COPY puppet /puppet
    RUN cd /puppet; FACTER_fqdn=localhost puppet apply \
      --modulepath=/usr/share/openstack-puppet/modules \
      node.pp

Running this yields:

    Error: Could not start Service[sshd]: Execution of '/sbin/service
      sshd start' returned 1: Redirecting to /bin/systemctl start  sshd.service
    Failed to get D-Bus connection: No connection to service manager.
    Wrapped exception:
    Execution of '/sbin/service sshd start' returned 1: Redirecting to
      /bin/systemctl start  sshd.service
    Failed to get D-Bus connection: No connection to service manager.

This is happening because the Puppet module is trying to manipulate
the corresponding service resource, but there is no service manager
(e.g., "systemd" or "upstart", etc) inside the container.  

Some modules provide a module parameter to disable service management,
but that solution isn't available in this module.  Instead, I created
a "dummy" service provider.  The "code" (or lack thereof) looks like
this:

    Puppet::Type.type(:service).provide :dummy, :parent => :base do
      desc "Dummy service provider"

      def startcmd
          true;
      end

      def stopcmd
          true;
      end

      def restartcmd
        true
      end

      def statuscmd
        true
      end
    end

I dropped this into a `dummy_service` puppet module with the
following structure:

    dummy_service/
      lib/
        puppet/
          provider/
            service/
              dummy.rb

I installed the whole thing into `/usr/share/puppet/modules` in the
base image (`larsks/rdo-puppet-base`) by adding the following to the
relevant `Dockerfile`:

    COPY dummy_service /usr/share/puppet/modules/dummy_service

I modified the `Dockerfile` for my ssh image to look like this:

    FROM larsks/rdo-puppet-base

    COPY puppet /puppet
    RUN cd /puppet; \
      FACTER_fqdn=localhost \
      puppet apply \
        --modulepath=/usr/share/openstack-puppet/modules:/usr/share/puppet/modules \
        node.pp

And finally I modified `node.pp` to look like this:

    Service {
      provider => dummy,
    }

    class { 'ssh': }

This sets the default `provider` for `service` resources to `dummy`.

With these changes, the `docker build` operation completes
successfully:

    Sending build context to Docker daemon 49.15 kB
    Sending build context to Docker daemon 
    Step 0 : FROM larsks/rdo-puppet-base
     ---> 2554b6fb47bb
    Step 1 : COPY puppet /puppet
     ---> Using cache
     ---> bf867271fd0f
    Step 2 : RUN cd /puppet; 	FACTER_fqdn=localhost 	puppet apply 		--modulepath=/usr/share/openstack-puppet/modules:/usr/share/puppet/modules 		node.pp
     ---> Running in 91b08a7a0ff5
    Notice: Compiled catalog for c6f07ae86c40.redhat.com in environment production in 0.58 seconds
    Notice: /Stage[main]/Ssh::Server::Install/Package[openssh-server]/ensure: created
    Notice: /Stage[main]/Ssh::Client::Config/File[/etc/ssh/ssh_config]/content: content changed '{md5}e233b9bb27ac15b968d8016d7be7d7ce' to '{md5}34815c31785be0c717f766e8d2c8d4d7'
    Notice: Finished catalog run in 47.61 seconds
     ---> e830e6adce26
    Removing intermediate container 91b08a7a0ff5
    Successfully built e830e6adce26

Obviously, in order to turn this into a functional module you would
need to add an appropriate `CMD` or `ENTRYPOINT` script to make it
generate host keys and start `sshd`, but I think this successfully
demonstrates what is necessary to make a stock Puppet module run
as part of the `docker build` process.

