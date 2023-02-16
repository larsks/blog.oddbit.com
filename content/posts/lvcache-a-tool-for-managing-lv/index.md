---
categories: [tech]
aliases: ["/2014/08/16/lvcache-a-tool-for-managing-lv/"]
title: "lvcache: a tool for managing LVM caches"
date: "2014-08-16"
tags:
  - lvm
  - cache
---

Until recently I had a [bcache][] based setup on my laptop, but when
forced by circumstance to reinstall everything I spent some time
looking for alternatives that were less disruptive to configure on an
existing system.

[bcache]: http://bcache.evilpiepirate.org/

I came across [Richard Jones' article][rjones] discussing the recent work to
integrate [dm-cache][] into [LVM][].  Unlike *bcache* and unlike using
*dm-cache* directly, the integration with LVM makes it easy to
associate devices with an existing logical volume.

[rjones]: http://rwmj.wordpress.com/2014/05/22/using-lvms-new-cache-feature/
[dm-cache]: https://en.wikipedia.org/wiki/Dm-cache
[lvm]: http://en.wikipedia.org/wiki/Logical_Volume_Manager_(Linux)

I have put together a small tool called [lvcache][] that simplies the
process of:

- Creating and attaching cache volumes
- Detaching and removing cache volumes
- Getting cache statistics for logical volumes
- Listing the cache status of all logical volumes

With `lvcache` installed, you can run (as root) the following command
to create a new cache volume that is 20% the size of your origin
volume and attach it to the specified origin volume:

    # lvcache create myvg/home

You can control the size of the cache LV relative to the origin
volume.  To create a cache LV that is 40% the size of the origin
volume:

    # lvcache create -% 40 myvg/home

You can query `dm-setup` for cache statistics with the `status`
command (the `-H` translates raw bytes counts into human readable
numbers with SI suffixes):

    # lvcache status -H myvg/home
    +-----------------------+------------------+
    | Field                 | Value            |
    +-----------------------+------------------+
    | cached                | True             |
    | size                  | 32G              |
    | cache_lv              | home_cache       |
    | cache_lv_size         | 6G               |
    | metadata_lv           | home_cache_cmeta |
    | metadata_lv_size      | 8M               |
    | cache_block_size      | 128              |
    | cache_utilization     | 0/98304          |
    | cache_utilization_pct | 0.0              |
    | demotions             | 0                |
    | dirty                 | 0                |
    | end                   | 62914560         |
    | features              | 1                |
    | md_block_size         | 8                |
    | md_utilization        | 200/2048         |
    | md_utilization_pct    | 9.765625         |
    | promotions            | 0                |
    | read_hits             | 0                |
    | read_misses           | 0                |
    | segment_type          | cache            |
    | start                 | 0                |
    | write_hits            | 0                |
    | write_misses          | 0                |
    +-----------------------+------------------+

Because `lvcache` is using the [cliff][] framework, it is very easy to
extract individual values from this list for graphing or monitoring
purposes:

[cliff]: http://cliff.readthedocs.org/en/latest/

    # lvcache status tank.home -f value -c md_utilization_pct
    9.765625

Or:

    # lvcache status tank.home -f shell
    cached="True"
    size="32G"
    cache_lv="nova_cache"
    cache_lv_size="6G"
    metadata_lv="nova_cache_cmeta"
    metadata_lv_size="8M"
    cache_block_size="128"
    cache_utilization="0/98304"
    cache_utilization_pct="0.0"
    demotions="0"
    dirty="0"
    end="62914560"
    features="1"
    md_block_size="8"
    md_utilization="200/2048"
    md_utilization_pct="9.765625"
    promotions="0"
    read_hits="0"
    read_misses="0"
    segment_type="cache"
    start="0"
    write_hits="0"
    write_misses="0"

This is a very rough tool right now, but it seems to get the job done
on my system.  If you do find this useful, let me know!


[lvcache]: https://github.com/larsks/lvcache

