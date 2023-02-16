---
categories: [tech]
aliases: ["/2010/02/19/apache-virtual-host-statistics/"]
title: Apache virtual host statistics
date: "2010-02-19"
tags:
  - release
  - apache
  - visualization
  - logging
  - software
---

As part of a project I'm working on I wanted to get a rough idea of the activity of the Apache virtual hosts on the system. I wasn't able to find exactly what I wanted, so I refreshed my memory of curses to bring you _vhoststats_.

This tools reads an Apache log file (with support for arbitrary formats) and generates a dynamic bar chart showing the activity (in number of requests and bytes transferred) of hosts on the system. The output might look something like this (but with colors):
    
    
    [2010/02/19 20:21:32] Hosts: 7 [Displayed: 7] Requests: 104
    
    host1.companyA.com   [R:1         ]  #
                         [B:3         ]
    devel.internal       [R:1         ]  #
                         [B:208       ]
    host2.companyA.com   [R:1         ]  #
                         [B:4499      ]
    A-truncated-host-nam [R:10        ]  ############
                         [B:65380     ]  #
    host1.companyB.com   [R:21        ]  ##########################
                         [B:166715    ]  ####
    www.google.com       [R:32        ]  #################################
                         [B:1566614   ]  ####################################
    

The tool keeps running totals over a five minute window, but you can change the window size on the command line. You can tail your active access log to see live results, or for a more exciting display you can just pipe in an existing log.

It's not [pong][1], but I've found it useful.

You can download the code from the [project page][2] on GitHub.

[1]: http://code.google.com/p/logstalgia/
[2]: http://github.com/larsks/vhoststats/

