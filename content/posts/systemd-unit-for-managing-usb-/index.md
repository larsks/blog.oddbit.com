---
categories: [tech]
aliases: ["/2018/10/19/systemd-unit-for-managing-usb-/"]
title: Systemd unit for managing USB gadgets
date: "2018-10-19"
tags:
- raspberrypi
- usb
---

The Pi Zero (and Zero W) have support for acting as a USB [gadget][]:
that means that they can be configured to act as a USB device -- like
a serial port, an ethernet interface, a mass storage device, etc.

[gadget]: http://www.linux-usb.org/gadget/

There are two different ways of configuring this support.  The first
only allows you to configure a single type of gadget at a time, and
boils down to:

1. Enable the dwc2 overlay in `/boot/config.txt`
1. Reboot.
1. `modprobe g_serial`

This process is more fully documented [here][].

[here]: https://learn.adafruit.com/turning-your-raspberry-pi-zero-into-a-usb-gadget/overview

The second mechanism makes use of the `libcomposite` driver to create
multifunction gadgets.  The manual procedure is documented in [the
kernel documentation][]. While it's a useful feature, the
configuration process requires several steps and if you only do it
infrequently it can be easy to forget.

[the kernel documentation]: https://www.kernel.org/doc/Documentation/usb/gadget_configfs.txt

In order to make this easier for me to manage, I've wrapped the
process up in a [systemd template unit][] that takes care of the
various steps necessary to both create and remove a multifunction USB
gadget.

[systemd template unit]: https://fedoramagazine.org/systemd-template-unit-files/

Once installed, creating a gadget that offers both a serial interface
and a network interface is as simple as:

1. Create a file `/etc/gadget/g0.conf` containing:

        USB_FUNCTIONS="rndis.usb0 acm.usb0"

1. Run `systemctl start usb-gadget@g0`.

You can remove the gadget by running `systemctl stop usb-gadget@g0`.
As with any systemd service, you can mark the unit to start
automatically when your system boots by running `systemctl enable
usb-gadget@g0`.

The [systemd-usb-gadget][] project can be found at:

- https://github.com/larsks/systemd-usb-gadget

[systemd-usb-gadget]: https://github.com/larsks/systemd-usb-gadget
