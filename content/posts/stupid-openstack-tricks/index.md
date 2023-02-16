---
categories: [tech]
aliases: ["/2014/01/16/stupid-openstack-tricks/"]
title: Stupid OpenStack Tricks
date: "2014-01-16"
tags:
- openstack
- tricks
---

I work with several different OpenStack installations.  I usually work
on the command line, sourcing in an appropriate `stackrc` with
credentials as necessary, but occasionally I want to use the dashboard
for something.

For all of the deployments with which I work, the keystone endpoint is
on the same host as the dashboard.  So rather than trying to remember
which dashboard url I want for the environment I'm currently using on
the command line, I put together this shell script:

    #!/bin/sh

    url=${OS_AUTH_URL%:*}/
    exec xdg-open $url

This takes the value of your `OS_AUTH_URL` environment variable,
strips off everything after the port specification, and passes that to
your default browser.

