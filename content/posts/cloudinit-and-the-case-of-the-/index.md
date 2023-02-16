---
aliases:
- /2014/12/10/cloudinit-and-the-case-of-the-changing-hostname/
- /post/2014-12-10-cloudinit-and-the-case-of-the-changing-hostname
categories:
- tech
date: '2014-12-10'
tags:
- openstack
- rdo
- neutron
title: Cloud-init and the case of the changing hostname
---

## Setting the stage

I ran into a problem earlier this week deploying RDO Icehouse under
RHEL 6.  My target systems were a set of libvirt guests deployed from
the RHEL 6 KVM guest image, which includes [cloud-init][] in order to
support automatic configuration in cloud environments.  I take
advantage of this when using `libvirt` by attaching a configuration
drive so that I can pass in ssh keys and a `user-data` script.

[cloud-init]: https://cloudinit.readthedocs.org/en/latest/

Once the systems were up, I used [packstack][] to deploy OpenStack
onto a single controller and two compute nodes, and at the conclusion
of the `packstack` run everything was functioning correctly.  Running
`neutron agent-list` showed all agents in good order:

[packstack]: https://wiki.openstack.org/wiki/Packstack

    +--------------------------------------+--------------------+------------+-------+----------------+
    | id                                   | agent_type         | host       | alive | admin_state_up |
    +--------------------------------------+--------------------+------------+-------+----------------+
    | 0d51d200-d902-4e05-847a-858b69c03088 | DHCP agent         | controller | :-)   | True           |
    | 192f76e9-a816-4bd9-8a90-a263a1d54031 | Open vSwitch agent | compute-0  | :-)   | True           |
    | 3d97d7ba-1b1f-43f8-9582-f860fbfe50df | Open vSwitch agent | controller | :-)   | True           |
    | 54d387a6-dca1-4ace-8c1b-7788fb0bc090 | Metadata agent     | controller | :-)   | True           |
    | 92fc83bf-0995-43c3-92d1-70002c734604 | L3 agent           | controller | :-)   | True           |
    | e06575c2-43b3-4691-80bc-454f501debfe | Open vSwitch agent | compute-1  | :-)   | True           |
    +--------------------------------------+--------------------+------------+-------+----------------+

## A problem rears its ugly head

After rebooting the system, I found that I was missing an expected
Neutron router namespace.  Specifically, given:

    # neutron router-list
    +--------------------------------------+---------+-----------------------------------------------------------------------------+
    | id                                   | name    | external_gateway_info                                                       |
    +--------------------------------------+---------+-----------------------------------------------------------------------------+
    | e83eec10-0de2-4bfa-8e58-c1bcbe702f51 | router1 | {"network_id": "b53a9ecd-01fc-4bee-b20d-8fbe0cd2e010", "enable_snat": true} |
    +--------------------------------------+---------+-----------------------------------------------------------------------------+

I expected to see:

    # ip netns
    qrouter-e83eec10-0de2-4bfa-8e58-c1bcbe702f51

But the `qrouter` namespace was missing.

The output of `neutron agent-list` shed some light on the problem:

    +--------------------------------------+--------------------+------------------------+-------+----------------+
    | id                                   | agent_type         | host                   | alive | admin_state_up |
    +--------------------------------------+--------------------+------------------------+-------+----------------+
    | 0832e8f3-61f9-49cf-b49c-886cc94d3d28 | Metadata agent     | controller.localdomain | :-)   | True           |
    | 0d51d200-d902-4e05-847a-858b69c03088 | DHCP agent         | controller             | xxx   | True           |
    | 192f76e9-a816-4bd9-8a90-a263a1d54031 | Open vSwitch agent | compute-0              | :-)   | True           |
    | 3be34828-ca8d-4638-9b3a-4e2f688a9ca9 | L3 agent           | controller.localdomain | :-)   | True           |
    | 3d97d7ba-1b1f-43f8-9582-f860fbfe50df | Open vSwitch agent | controller             | xxx   | True           |
    | 54d387a6-dca1-4ace-8c1b-7788fb0bc090 | Metadata agent     | controller             | xxx   | True           |
    | 87b53741-f28b-4582-9ea8-6062ab9962e9 | Open vSwitch agent | controller.localdomain | :-)   | True           |
    | 92fc83bf-0995-43c3-92d1-70002c734604 | L3 agent           | controller             | xxx   | True           |
    | e06575c2-43b3-4691-80bc-454f501debfe | Open vSwitch agent | compute-1              | :-)   | True           |
    | e327b7f9-c9ce-49f8-89c1-b699d9f7d253 | DHCP agent         | controller.localdomain | :-)   | True           |
    +--------------------------------------+--------------------+------------------------+-------+----------------+

There were two sets of Neutron agents registered using different
hostnames -- one set using the short name of the host, and the other
set using the fully qualified hostname.

## What's up with that?

In the `cc_set_hostname.py` module, `cloud-init` performs the
following operation:

    (hostname, fqdn) = util.get_hostname_fqdn(cfg, cloud)
    try:
        log.debug("Setting the hostname to %s (%s)", fqdn, hostname)
        cloud.distro.set_hostname(hostname, fqdn)
    except Exception:
        util.logexc(log, "Failed to set the hostname to %s (%s)", fqdn,
                    hostname)
        raise

It starts by retrieving the hostname (both the qualified and
unqualified version) from the cloud environment, and then calls
`cloud.distro.set_hostname(hostname, fqdn)`.  This ends up calling:

    def set_hostname(self, hostname, fqdn=None):
        writeable_hostname = self._select_hostname(hostname, fqdn)
        self._write_hostname(writeable_hostname, self.hostname_conf_fn)
        self._apply_hostname(hostname)

Where, on a RHEL system, `_select_hostname` is:

    def _select_hostname(self, hostname, fqdn):
        # See: http://bit.ly/TwitgL
        # Should be fqdn if we can use it
        if fqdn:
            return fqdn
        return hostname

So:

- `cloud-init` sets `writeable_hostname` to the fully qualified name
  of the system (assuming it is available).
- `cloud-init` writes the fully qualified hostname to `/etc/sysconfig/network`.
- `cloud-init` sets the hostname to the *unqualified* hostname

The result is that your system will probably have a different hostname
after your first reboot, which throws off Neutron.

## And they all lived happily ever after?

It turns out this bug was reported upstream back in October of 2013 as
[bug 1246485][], and while there are patches available the bug has
been marked as "low" priority and has been fixed.  There are patches
attached to the bug report that purport to fix the problem.

[bug 1246485]:  https://bugs.launchpad.net/cloud-init/+bug/1246485