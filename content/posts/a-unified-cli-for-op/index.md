---
categories: [tech]
aliases: ["/2013/11/22/a-unified-cli-for-op/"]
title: A unified CLI for OpenStack
date: "2013-11-22"
tags:
  - openstack
---

The [python-openstackclient][1] project, by [Dean Troyer][] and
others, is a new command line tool to replace the existing command
line clients (including commands such as `nova`, `keystone`, `cinder`,
etc).

[dean troyer]: https://github.com/dtroyer

This tool solves two problems I've encountered in the past:

- Command line options between different command line clients are
  sometimes inconsistent.

- The output from the legacy command line tools is not designed to be
  machine parse-able (and yet people [do it anyway][1]).

The new `openstack` CLI framework is implement using the [cliff][3]
module for Python, which will help enforce a consistent interface to
the various subcommands (because common options can be shared, and
just having everything in the same codebase will help tremendously).
Cliff also provides flexible table formatters.  It includes a number
of useful formatters out of the box, and can be extended via
setuptools entry points.

The `csv` formatter can be used to produce machine parse-able output
from list commands.  For example:

    $ openstack -q endpoint list -f csv --quote none
    ID,Region,Service Name,Service Type
    ba686936d31846f5b226539dba285654,RegionOne,quantum,network
    161684fd123740138c8806267c489766,RegionOne,cinder,volume
    b2019dbef5f34d1bb809e8e399369782,RegionOne,keystone,identity
    4b5dd8c6b961442ba13d6b9d317d718a,RegionOne,swift_s3,s3
    ac766707ffa3437eaaeaafa3c3eace08,RegionOne,swift,object-store
    e3f7bd37b51341bbaa77f81ba39a3bf2,RegionOne,glance,image
    6821fad71a914636af6e98775e52e1ec,RegionOne,nova_ec2,ec2
    3b2a90e9f85a468988af763c707961d7,RegionOne,nova,compute

For "show" commands, the `shell` formatter produces output in
`name=value` format, like this:

    $ openstack -q endpoint show image -f shell --all
    adminurl="http://192.168.122.110:9292"
    id="e3f7bd37b51341bbaa77f81ba39a3bf2"
    internalurl="http://192.168.122.110:9292"
    publicurl="http://192.168.122.110:9292"
    region="RegionOne"
    service_id="14a1479f77274dd485e9fb52af2e1721"
    service_name="glance"
    service_type="image"

This output could easily be sourced into a shell script.

[1]: https://github.com/openstack/python-openstackclient
[2]: https://github.com/stackforge/puppet-keystone/blob/e100e057bb2f6517fc6c5caad46a053864aa5328/lib/puppet/provider/keystone.rb#L167
[3]: https://github.com/dreamhost/cliff

