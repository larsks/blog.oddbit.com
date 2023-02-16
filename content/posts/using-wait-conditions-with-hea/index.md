---
categories: [tech]
aliases: ["/2014/08/30/using-wait-conditions-with-hea/"]
title: Using wait conditions with Heat
date: "2014-08-30"
tags:
  - openstack
  - heat
---

This post accompanies my [article on the Docker plugin for
Heat][1].

In order for `WaitCondition` resources to operate correctly in Heat, you
will need to make sure that that you have:

- Created the necessary Heat domain and administrative user in
  Keystone,
- Configured appropriate values in `heat.conf` for
  `stack_user_domain`, `stack_domain_admin`, and
  `stack_domain_admin_password`.
- Configured an appropriate value in `heat.conf` for
  `heat_waitcondition_server_url`.  On a single-system install this
  will often be pointed by default at `127.0.0.1`, which, hopefully for
  obvious reasons, won't be of any use to your Nova servers.
- Enabled the `heat-api-cfn` service,
- Configured your firewall to permit access to the CFN service (which
  runs on port 8000).

Steve Hardy has a blog post on [stack domain users][2] that goes into
detail on configuring authentication for Heat and Keystone.

[1]: {{< ref "docker-plugin-for-openstack-he" >}}
[2]: http://hardysteven.blogspot.co.uk/2014/04/heat-auth-model-updates-part-2-stack.html

