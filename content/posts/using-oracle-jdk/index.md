---
categories: [tech]
aliases: ["/2012/11/26/using-oracle-jdk/"]
title: Using Oracle JDK under CentOS
date: "2012-11-26"
---

I needed to replace the native OpenJDK based Java VM with the Oracle
Java distribution on one of our CentOS servers.  In order to do it
cleanly I wanted to set up the `alternatives` system to handle it, but
it took a while to figure out the exact syntax.

For the record (and because I will probably forget):

    alternatives --install /usr/bin/java java /usr/java/latest/bin/java 2000 \
      --slave /usr/bin/keytool keytool /usr/java/latest/bin/keytool \
      --slave /usr/bin/rmiregistry rmiregistry /usr/java/latest/bin/rmiregistry

