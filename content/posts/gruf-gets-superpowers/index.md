---
categories: [tech]
aliases: ["/2016/02/19/gruf-gets-superpowers/"]
title: "Gruf gets superpowers"
date: "2016-02-19"
tags:
  - gerrit
  - gruf
---

In my [last article][last] article I introduced [Gruf][], a command line
tool for interacting with [Gerrit][].  Since then, Gruf has gained a
few important new features.

[gruf]: http://github.com/larsks/gruf

## Caching

Gruf will now by default cache results for five minutes.  This avoids
repeatedly querying the server for the same information when you're
just displaying it with different templates (for example, if you run a
`gruf query open here` followed by a `gruf -t patches query open
here`).

The cache lifetime can be tuned on the command line (with the
`--cache-lifetime` option) or in the `gruf.yml` configuration file (as
the `cache_lifetime` parameter).  Gruf has also learned the
`invalidate-cache` command if you want to clear out the cache.

## Better streaming

I have substantially enhanced the support for the Gerrit
[stream-events][] command.

### Automatic reconnection

Gruf will now automatically reconnect to the Gerrit server if the
connection is lost while streaming events.

### Better default templates

The default `stream-events` template now produces colorized output,
and there is also a `short` template that produces one or two line
output for each event that can be useful if you just want to see
what's going on.

The default output looks like this:

<pre>
[<span style="color:#00f0f0;">PATCH</span>     ] 282340,1 openstack/gnocchi
           URL: https://review.openstack.org/282340
           Author: Chaozhe Chen(ccz) (Chaozhe.Chen) &lt;chaozhe.chen&#64;easystack.cn&gt;
           Topic: update-flake8
           Subject: Use '#flake8: noqa' to skip file check

[<span style="color:#00f0f0;">PATCH</span>     ] 281835,2 openstack/nova
           URL: https://review.openstack.org/281835
           Author: Roman Dobosz (gryf) &lt;roman.dobosz&#64;intel.com&gt;
           Topic: bug-1546433
           Subject: Add annotation to the kill() method

[<span style="color:#f0f000;">COMMENT</span>   ] 282324,3 openstack/fuel-octane
           URL: https://review.openstack.org/282324
           Author: Yuriy Taraday (yorik-sar) &lt;yorik.sar&#64;gmail.com&gt;
           Topic: 282317
           Subject: Remove unused password param from restore command

    Patch Set 3: Code-Review+2 Workflow+1
</pre>


The short output looks something like this:

<pre>
[<span style="color:#00f0f0;">PATCH</span>     ] 240944,24 openstack/python-ironicclient sturivnyi <span style="color:#0000f0;">https://review.openstack.org/240944</span>
             Add sanity tests for testing actions with Port
[<span style="color:#f0f000;">COMMENT</span>   ] 282334,1 openstack/fuel-octane gelbuhos <span style="color:#0000f0;">https://review.openstack.org/282334</span>
             Workflow 1 Code-Review 2 
[<span style="color:#f0f000;">COMMENT</span>   ] 282334,1 openstack/fuel-octane gelbuhos <span style="color:#0000f0;">https://review.openstack.org/282334</span>
[<span style="color:#f0f000;">COMMENT</span>   ] 275844,23 openstack/kolla elemoine <span style="color:#0000f0;">https://review.openstack.org/275844</span>
             Workflow 1 Code-Review 2 
[<span style="color:#f0f000;">COMMENT</span>   ] 279478,3 openstack/fuel-octane gelbuhos <span style="color:#0000f0;">https://review.openstack.org/279478</span>
             Verified 2 
[<span style="color:#00f000;">MERGED</span>    ] 279478,3 openstack/fuel-octane gelbuhos <span style="color:#0000f0;">https://review.openstack.org/279478</span>
[<span style="color:#f0f000;">COMMENT</span>   ] 248938,29 openstack/neutron slaweq <span style="color:#0000f0;">https://review.openstack.org/248938</span>
[<span style="color:#f0f000;">COMMENT</span>   ] 279478,3 openstack/fuel-octane gelbuhos <span style="color:#0000f0;">https://review.openstack.org/279478</span>
[<span style="color:#f0f000;">COMMENT</span>   ] 279478,3 openstack/fuel-octane gelbuhos <span style="color:#0000f0;">https://review.openstack.org/279478</span>
[<span style="color:#f0f000;">COMMENT</span>   ] 276419,1 openstack/glance siuzannatb <span style="color:#0000f0;">https://review.openstack.org/276419</span>
             Workflow 1 Code-Review 2 
[<span style="color:#f0f000;">COMMENT</span>   ] 276814,18 openstack/fuel-web vkramskikh <span style="color:#0000f0;">https://review.openstack.org/276814</span>
             Verified 1 
[<span style="color:#f0f000;">COMMENT</span>   ] 276419,1 openstack/glance siuzannatb <span style="color:#0000f0;">https://review.openstack.org/276419</span>
[<span style="color:#f0f000;">COMMENT</span>   ] 281472,2 openstack/ironic-webclient krotscheck <span style="color:#0000f0;">https://review.openstack.org/281472</span>
             Verified 1 
[<span style="color:#f0f000;">COMMENT</span>   ] 282331,1 openstack/fuel-qa apanchenko <span style="color:#0000f0;">https://review.openstack.org/282331</span>
</pre>

[last]: {{< ref "gruf-a-gerrit-command-line-uti" >}}
[gerrit]: https://www.gerritcodereview.com/
[stream-events]: https://gerrit.googlecode.com/svn/documentation/2.1.2/cmd-stream-events.html
