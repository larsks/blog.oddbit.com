---
categories: [tech]
aliases: ["/2018/03/27/multiple-1-wire-buses-on-the-/"]
title: Multiple 1-Wire Buses on the Raspberry Pi
date: "2018-03-27"
tags:
- hardware
- raspberrypi
- onewire
- iot
cover: onewire.jpg
---

The DS18B20 is a popular temperature sensor that uses the [1-Wire][]
protocol for communication. Recent versions of the Linux kernel
include a kernel driver for this protocol, making it relatively
convenient to connect one or more of these devices to a Raspberry Pi
or similar device.  1-Wire devices can be daisy chained, so it is
possible to connect several devices to your Pi using only a single
GPIO pin, and you'll find many articles out there that describe how to
do so.

[1-wire]: https://en.wikipedia.org/wiki/1-Wire

Occasionally, it may be necessary to have more than a single chain of
connected devices.  For example, you may have reached the limits on
the size of your 1-Wire network, or you may simply need to route your
cables in a way that makes a single chain difficult.  You can enable
*multiple* 1-Wire buses on your Raspberry Pi to handle these
situations.

For a single 1-Wire bus, you add the following to `/boot/config.txt`:

    dtoverlay=w1-gpio

This will enable the 1-Wire bus on GPIO 4.  To enable *multiple*
1-Wire buses, you will use multiple `dtoverlay` statements and the
`gpiopin` parameter to the `w1-gpio` overlay.  For example, to enable
1-Wire buses on GPIO 4 and GPIO 17, you would use:

    dtoverlay=w1-gpio,gpiopin=4
    dtoverlay=w1-gpio,gpiopin=17

In the picture at the top of this post, there are four DS18B20
sensors.  Three are connected to the 1-Wire bus on GPIO 4, and one is
connected to the 1-Wire bus on GPIO 17.  Looking in
`/sys/bus/w1/devices`, I see two w1_bus_master devices (and the four
temperature sensors):

    $ ls /sys/bus/w1/devices/
    28-041722cbacff  28-0417231547ff  w1_bus_master1
    28-041722ce24ff  28-04172318c0ff  w1_bus_master2

I can check the temperature on all four devices like this:

    $ cat /sys/bus/w1/devices/28-*/w1_slave
    50 01 4b 46 7f ff 0c 10 e8 : crc=e8 YES
    50 01 4b 46 7f ff 0c 10 e8 t=21000
    50 01 4b 46 7f ff 0c 10 e8 : crc=e8 YES
    50 01 4b 46 7f ff 0c 10 e8 t=21000
    57 01 4b 46 7f ff 0c 10 38 : crc=38 YES
    57 01 4b 46 7f ff 0c 10 38 t=21437
    57 01 4b 46 7f ff 0c 10 38 : crc=38 YES
    57 01 4b 46 7f ff 0c 10 38 t=21437

You may have noted that there is also a DHT22 sensor in the picture.
Much like the 1-Wire overlay, the kernel driver for the DHT22 can be
associated with an arbitrary GPIO pin like this:

    dtoverlay=dht11,gpiopin=27
