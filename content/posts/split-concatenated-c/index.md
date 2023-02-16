---
categories: [tech]
aliases: ["/2013/07/16/split-concatenated-c/"]
title: Split concatenated certificates with awk
date: "2013-07-16"
tags:
  - awk
---

[This][] is a short script that takes a list of concatenated
certificates as input (such as a collection of CA certificates) and
produces a collection of numbered files, each containing a single
certificate.

    #!/bin/awk -f
     
    # This script expects a list of concatenated certificates on input and
    # produces a collection of individual numbered files each containing
    # a single certificate.
     
    BEGIN {incert=0}
     
    /-----BEGIN( TRUSTED)? CERTIFICATE-----/ {
    certno++
    certfile=sprintf("cert-%d.crt", certno)
    incert=1
    }
     
    /-----END( TRUSTED)? CERTIFICATE-----/ {
    print >> certfile
    incert=0
    }
     
    incert==1 { print >> certfile }

[this]: https://gist.github.com/larsks/6008833

