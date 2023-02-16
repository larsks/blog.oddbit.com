---
categories: [tech]
aliases: ["/2018/02/08/listing-iptables-rules-with-li/"]
title: Listing iptables rules with line numbers
date: "2018-02-08"
tags:
- shell
- iptables
---

You can list `iptables` rules with rule numbers using the
`--line-numbers` option, but this only works in list (`-L`) mode.  I
find it much more convenient to view rules using the output from
`iptables -S` or `iptables-save`.

You can augment the output from these commands with rule numbers with
the following `awk` script:

    #!/bin/awk -f

    state == 0 && /^-A/ {state=1; chain=$2; counter=1; printf "\n"}
    state == 1 && $2 != chain {chain=$2; counter=1; printf "\n"}
    !/^-A/ {state=0}
    state == 1 {printf "[%03d] %s\n", counter++, $0}
    state == 0 {print}

This will produce output along the lines of:

    -P INPUT ACCEPT
    -P FORWARD ACCEPT
    -P OUTPUT ACCEPT
    -N DOCKER
    -N DOCKER-ISOLATION
    -N LARS

    [001] -A INPUT -i virbr1 -p udp -m udp --dport 53 -j ACCEPT
    [002] -A INPUT -i virbr1 -p tcp -m tcp --dport 53 -j ACCEPT
    [003] -A INPUT -i virbr1 -p udp -m udp --dport 67 -j ACCEPT
    [004] -A INPUT -i virbr1 -p tcp -m tcp --dport 67 -j ACCEPT
    [005] -A INPUT -i virbr0 -p udp -m udp --dport 53 -j ACCEPT
    [006] -A INPUT -i virbr0 -p tcp -m tcp --dport 53 -j ACCEPT
    [007] -A INPUT -i virbr0 -p udp -m udp --dport 67 -j ACCEPT
    [008] -A INPUT -i virbr0 -p tcp -m tcp --dport 67 -j ACCEPT

    [001] -A FORWARD -j DOCKER-ISOLATION
    [002] -A FORWARD -o docker0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
    [003] -A FORWARD -o docker0 -j DOCKER
    [004] -A FORWARD -i docker0 ! -o docker0 -j ACCEPT
    [005] -A FORWARD -i docker0 -o docker0 -j ACCEPT

    [001] -A DOCKER-ISOLATION -i br-c9ab3aa72e98 -o docker0 -j DROP
    [002] -A DOCKER-ISOLATION -i docker0 -o br-c9ab3aa72e98 -j DROP
    [003] -A DOCKER-ISOLATION -i br-74ee392a7301 -o docker0 -j DROP
    [004] -A DOCKER-ISOLATION -i docker0 -o br-74ee392a7301 -j DROP
    [005] -A DOCKER-ISOLATION -i br-6b5fa040c423 -o docker0 -j DROP
    [006] -A DOCKER-ISOLATION -i docker0 -o br-6b5fa040c423 -j DROP
    [007] -A DOCKER-ISOLATION -i br-438e4f71d66d -o docker0 -j DROP
    [008] -A DOCKER-ISOLATION -i docker0 -o br-438e4f71d66d -j DROP

That makes it much easier if you're trying to insert or delete rules
by index (as in `iptables -I INPUT 7 ...`).  I keep the awk code itself
in a script named `number-rules` so that running it locally usually
looks like:

    # iptables -S | number-rules | less
