---
categories: [tech]
aliases: ["/2018/06/14/configuring-a-static-address-f/"]
title: Configuring a static address for wlan0 on Raspbian Stretch
date: "2018-06-14"
tags:
- networking
- raspberrypi
---

Recent releases of Raspbian have adopted the use of [dhcpcd][] to
manage both dynamic and static interface configuration.  If you would
prefer to use the traditional `/etc/network/interfaces` mechanism
instead, follow these steps.

[dhcpcd]: http://manpages.ubuntu.com/manpages/trusty/man8/dhcpcd5.8.html

1. First, disable `dhcpcd` and `wpa_supplicant`.

        systemctl disable --now dhdpcd wpa_supplicant

1. You will need a `wpa_supplicant` configuration for `wlan0` in
   `/etc/wpa_supplicant/wpa_supplicant-wlan0.conf`.
   
     If you already have an appropriate configuration in
   `/etc/wpa_supplicant/wpa_supplicant.conf`, you can just symlink the
   file:

         cd /etc/wpa_supplicant
         ln -s wpa_supplicant.conf wpa_supplicant-wlan0.conf

1. Enable the `wpa_supplicant` service for `wlan0`:

        systemctl enable --now wpa_supplicant@wlan0

1. Create an appropriate configuration in
   `/etc/network/interfaces.d/wlan0`.  For example:

        allow-hotplug wlan0

        iface wlan0 inet static
        address 192.168.2.100
        netmask 255.255.255.0

        iface wlan0 inet6 static
        address 2607:f0d0:2001:000a:0000:0000:0000:0010
        netmask 64

1. Reboot to make sure everything comes up as expected.  With the
   above configuration, after rebooting you should see:

        root@raspberrypi:~# ip addr show wlan0
        3: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
            link/ether 00:e1:b0:67:98:67 brd ff:ff:ff:ff:ff:ff
            inet 192.168.2.100/24 brd 192.168.2.255 scope global wlan0
               valid_lft forever preferred_lft forever
            inet6 2607:f0d0:2001:a::10/64 scope global
               valid_lft forever preferred_lft forever
            inet6 fe80::2e1:b0ff:fe67:9867/64 scope link
               valid_lft forever preferred_lft forever
