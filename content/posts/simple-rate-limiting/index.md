---
categories: [tech]
aliases: ["/2011/12/26/simple-rate-limiting/"]
title: Rate limiting made simple
date: "2011-12-26"
tags:
  - networking
  - linux
---

I use [CrashPlan][1] as a backup service. It works and is very simple to set
up, but has limited options for controlling bandwidth. In fact, if you're
running it on a headless system (e.g., a fileserver of some sort), your options
are effectively "too slow" and "CONSUME EVERYTHING". There is an [open
request][2] to add time-based limitations to the application itself, but for
now I've solved this using a very simple traffic shaping configuration.
Because the learning curve for "tc" and friends is surprisingly high, I'm
putting [my script](https://gist.github.com/larsks/4014881) here in the hopes
that other people might find it useful, and so that I can find it when I need
to do this again someday. 

    #!/bin/sh
     
    # The network device used for backups
    dev=p10p1
     
    # The remove address of the CrashPlanserver
    crashplan_addr=50.93.246.1
     
    # The port
    crashplan_port=443
     
    # The rate limit. See tc(8) for acceptable syntax.
    crashplan_limit=2mbit
     
    if [ "$1" = "enable" ]; then
        #
        # This creates and activates the traffic shaper
        # configuration.
        #
        logger -s -t ratelimit -p user.notice "enabling rate limits"
        tc qdisc del dev $dev root > /dev/null 2>&1
        tc qdisc add dev $dev root handle 1: htb
        tc class add dev $dev parent 1: classid 1:10 htb rate $crashplan_limit
        tc filter add dev $dev parent 1: prio 0 protocol ip handle 10 fw flowid 1:10
        iptables -t mangle -A OUTPUT -d $crashplan_addr -p tcp --dport $crashplan_port -j MARK --set-mark 10
    elif [ "$1" = "disable" ]; then
        #
        # This removes the traffic shaper
        # configuration.
        #
        logger -s -t ratelimit -p user.notice "disabling rate limits"
        tc qdisc del dev $dev root > /dev/null 2>&1
        iptables -t mangle -D OUTPUT -d $crashplan_addr -p tcp --dport $crashplan_port -j MARK --set-mark 10
    elif [ "$1" = "show" ]; then
        #
        # Shows the current traffic shaper configuration.
        #
        tc qdisc show dev $dev
        tc class show dev $dev
        tc filter show dev $dev
        iptables -t mangle -vnL OUTPUT
    fi

[1]: http://www.crashplan.com/
[2]: https://crashplan.zendesk.com/entries/446273-throttle-bandwidth-by-hours?page=1#post_20799486

