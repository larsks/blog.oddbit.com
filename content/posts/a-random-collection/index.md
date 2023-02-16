---
categories: [tech]
aliases: ["/2013/11/12/a-random-collection/"]
title: A random collection of OpenStack Tools
date: "2013-11-12"
tags:
  - openstack
---

I've been working with [OpenStack][] a lot recently, and I've ended up with a small collection of utilities that make my life easier.  On the odd chance that they'll make your life easier, too, I thought I'd hilight them here.

<!-- more -->

## Crux

[Crux][] is a tool for provisioning tenants, users, and roles in keystone.  Instead of a sequence of keystone command, you can provision new tenants, users, and roles with a single comand.

For example, to create user `demo` in the `demo` tenant with password secret:

    # crux --user demo:demo::secret
    2013-10-21 crux WARNING creating tenant demo
    2013-10-21 crux WARNING creating user demo with password secret

Crux is in general idempotent; if we were to run the same command a second time we woudl see:

    # crux --user demo:demo::secret
    2013-10-21 crux WARNING set password for user demo to secret
    
Crux can also take input from a configuration file, so you can quickly set up a complex set of tenants and users.

## Sqlcli

[Sqlcli][] uses [SQLAlchemy][] to run SQL queries against a variety of backends specified by SQL connection URLs.  I wrote this to perform queries and simple maintenance against the various databases used by OpenStack.  For example, you can get a list of networks from the Neutron database with a command like this:

    # sqlcli -f /etc/neutron/plugin.ini -i DATABASE/sql_connection \
      'select name,cidr from subnets'

And get output like this:

    public,172.24.4.224/28
    net0-subnet0,10.0.0.0/24

You can add the `--pretty` flag and get output like this:

    +--------------+-----------------+
    |     name     |       cidr      |
    +--------------+-----------------+
    |    public    | 172.24.4.224/28 |
    | net0-subnet0 |   10.0.0.0/24   |
    +--------------+-----------------+

## openstack-service

The [openstack-service][osctl] command is a convenience tool for managing OpenStack services.  It lets you start/stop or query the status of groups of related services.  For example, if you want to see the status of all your Cinder services, you can run:

    # openstack-service status cinder
    
And get:

    openstack-cinder-api (pid  11644) is running...
    openstack-cinder-scheduler (pid  11790) is running...
    openstack-cinder-volume (pid  11712) is running...

You can stop all Cinder and Glance services like this:

    # openstack-service stop cinder glance
    Stopping openstack-cinder-api: [  OK  ]
    Stopping openstack-cinder-scheduler: [  OK  ]
    Stopping openstack-cinder-volume: [  OK  ]
    Stopping openstack-glance-api: [  OK  ]
    Stopping openstack-glance-registry: [  OK  ]

And start them back up again the same way:

    # openstack-service start cinder glance
    Starting openstack-cinder-api: [  OK  ]
    Starting openstack-cinder-scheduler: [  OK  ]
    Starting openstack-cinder-volume: [  OK  ]
    Starting openstack-glance-api: [  OK  ]
    Starting openstack-glance-registry: [  OK  ]

Without any additional arguments `openstack-service stop` will stop all OpenStack services on the current host.

[sqlalchemy]: http://www.sqlalchemy.org/
[openstack]: http://openstack.org/
[crux]: http://github.com/larsks/crux
[sqlcli]: http://github.com/larsks/sqlcli
[osctl]: http://github.com/larsks/osctl

