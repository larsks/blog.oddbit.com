---
aliases:
- /2010/02/24/ldap-redundancy-through-proxy-servers/
- /post/2010-02-24-ldap-redundancy-through-proxy-servers
categories:
- tech
date: '2010-02-24'
tags:
- balance
- ldap
- stunnel
- proxy
- ha
- howto
- ssl
title: LDAP redundancy through proxy servers
---

# Problem 1: Failover

## The problem

Many applications only allow you to configure a single LDAP server. This can lead to unnecessary service outages if your directory service infrastructure is highly available (e.g., you are running Active Directory) and your application cannot take advantage of this fact.

## A solution

We can provide a level of redundancy by passing the LDAP connections through a load balancing proxy. While this makes the proxy a single point of failure, it is (a) a very simple tool and thus less prone to complex failure modes, (b) running on the same host as the web application, and (c) is completely under our control.

For this example, I will use [Balance][1], a simple TCP load balancer from [Inlab Software GmbH][2]. There are packages available for most major Linux distributions, including [Fedora][3] and [CentOS][4].

Balance is configured completely on the command line. To provide round-robin access to a suite of three directory servers running LDAP over SSL, you might use the following command line:
    
    
    balance -b 127.0.0.1 636 10.1.1.1 10.1.1.2
    

Using balance's terminology, this creates one _group_ of two _channels_. Balance will round-robin among the channels in this group. Note that here and in subsequent examples we are binding the proxy to the loopback interface so that it is only available to applications running on the same host.

If you would prefer to preferentially send all the requests to the first server, and only use the second server if the first is unavailable, you could use a configuration like this:
    
    
    balance -b 127.0.0.1 636 10.1.1.1 \! 10.1.1.2
    

While you can run balance from a standard init (/etc/rc.d/...) script, I prefer to use a service manager such as [runit][5] which takes care of restarting the service if it should exit unexpectedly. You could achieve the same thing in a slightly less flexible fashion by putting your balance command line in /etc/inittab. In either case you need to add the -f option to the command line, which causes balance to stay in the foreground.

# Problem 2: Debugging LDAP over SSL

## The problem

It is convenient to use a packet tracer such as [Wireshark][6] to debug LDAP protocol errors. This is often more informative than the debugging information that will be available to you on the client side, and may be more useful than server side debugging in many cases, even supposing that you have administrative access to the directory servers.

## A solution

You can use [Stunnel][7], a general purpose SSL proxy tool, to intercept unencrypted client connections on the local machine and then forward them over an SSL channel to a remote server. This makes the unencrypted LDAP traffic available on the loopback interface while still ensuring that it is encrypted on the wire.

Stunnel can operate both as an SSL server and as an SSL client. In this case, we will be running it in client mode, connecting to a remote SSL server (or to the proxy configured in our previous example). Stunnel is configured by means of a simple INI-style configuration file. To achieve the goals of this example we might put the following configuration in a file (say, stunnel.conf):
    
    
    [ldap]
    
    accept = 127.0.0.1:389
    client = yes
    connect = localhost:636
    

We would run stunnel like this:
    
    
    stunnel /path/to/stunnel.conf
    

Again, I would run this under the control of a service supervisor. To keep stunnel in the foreground we would add the following to the global section of the configuration file (i.e., before the `[ldap]` section marker):
    
    
    foreground = yes
    

With both of these solutions in place, we have achieved the following:

  - High availability.

Our application will transparently make use of multiple directory servers. If a server fails, our application will continue to operate.

  - Security

Our traffic is encrypted on the wire, regardless of whether the application has support for LDAP over SSL.

  - Visibility

We are free to examine unencrypted traffic with a packet sniffer running on the local host.

[1]: http://www.inlab.de/balance.html
[2]: http://www.inlab.de/
[3]: http://fedoraproject.org/
[4]: http://www.centos.org/
[5]: http://smarden.org/runit/
[6]: http://www.wireshark.org/
[7]: http://www.stunnel.org/