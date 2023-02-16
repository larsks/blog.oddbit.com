---
categories:
- tech
date: '2022-02-13'
tags:
- linux
- micropython
- udev
title: 'Udev rules for CH340 serial devices'
---

I like to fiddle with [Micropython][], particularly on the [Wemos D1 Mini][wemos], because these are such a neat form factor. Unfortunately, they have a cheap CH340 serial adapter on board, which means that from the perspective of Linux these devices are all functionally identical -- there's no way to identify one device from another. This by itself would be a manageable problem, except that the device names assigned to these devices aren't constant: depending on the order in which they get plugged in (and the order in which they are detected at boot), a device might be `/dev/ttyUSB0` one day and `/dev/ttyUSB2` another day.

[wemos]: https://www.wemos.cc/en/latest/d1/d1_mini.html
[micropython]: https://micropython.org

On more than one occasion, I have accidentally re-flashed the wrong device. Ouch.

A common solution to this problem is to create device names based on the USB topology -- that is, assign names based on a device's position in the USB bus: e.g., when attaching a new USB serial device, expose it at something like `/dev/usbserial/<bus>/<device_path>`.  While that sounds conceptually simple, it took me a while to figure out the correct [udev][] rules.

[udev]: https://en.wikipedia.org/wiki/Udev

Looking at the available attributes for a serial device, we see:

```
# udevadm info -a -n /dev/ttyUSB0
[...]

  looking at device '/devices/pci0000:00/0000:00:1c.0/0000:03:00.0/usb3/3-1/3-1.4/3-1.4.3/3-1.4.3:1.0/ttyUSB0/tty/ttyUSB0':
    KERNEL=="ttyUSB0"
    SUBSYSTEM=="tty"
    DRIVER==""
    ATTR{power/control}=="auto"
    ATTR{power/runtime_active_time}=="0"
    ATTR{power/runtime_status}=="unsupported"
    ATTR{power/runtime_suspended_time}=="0"

  looking at parent device '/devices/pci0000:00/0000:00:1c.0/0000:03:00.0/usb3/3-1/3-1.4/3-1.4.3/3-1.4.3:1.0/ttyUSB0':
    KERNELS=="ttyUSB0"
    SUBSYSTEMS=="usb-serial"
    DRIVERS=="ch341-uart"
    ATTRS{port_number}=="0"
    ATTRS{power/control}=="auto"
    ATTRS{power/runtime_active_time}=="0"
    ATTRS{power/runtime_status}=="unsupported"
    ATTRS{power/runtime_suspended_time}=="0"

  looking at parent device '/devices/pci0000:00/0000:00:1c.0/0000:03:00.0/usb3/3-1/3-1.4/3-1.4.3/3-1.4.3:1.0':
    KERNELS=="3-1.4.3:1.0"
    SUBSYSTEMS=="usb"
    DRIVERS=="ch341"
    ATTRS{authorized}=="1"
    ATTRS{bAlternateSetting}==" 0"
    ATTRS{bInterfaceClass}=="ff"
    ATTRS{bInterfaceNumber}=="00"
    ATTRS{bInterfaceProtocol}=="02"
    ATTRS{bInterfaceSubClass}=="01"
    ATTRS{bNumEndpoints}=="03"
    ATTRS{supports_autosuspend}=="1"

  looking at parent device '/devices/pci0000:00/0000:00:1c.0/0000:03:00.0/usb3/3-1/3-1.4/3-1.4.3':
    KERNELS=="3-1.4.3"
    SUBSYSTEMS=="usb"
    DRIVERS=="usb"
    ATTRS{authorized}=="1"
    ATTRS{avoid_reset_quirk}=="0"
    ATTRS{bConfigurationValue}=="1"
    ATTRS{bDeviceClass}=="ff"
    ATTRS{bDeviceProtocol}=="00"
    ATTRS{bDeviceSubClass}=="00"
    ATTRS{bMaxPacketSize0}=="8"
    ATTRS{bMaxPower}=="98mA"
    ATTRS{bNumConfigurations}=="1"
    ATTRS{bNumInterfaces}==" 1"
    ATTRS{bcdDevice}=="0262"
    ATTRS{bmAttributes}=="80"
    ATTRS{busnum}=="3"
    ATTRS{configuration}==""
    ATTRS{devnum}=="8"
    ATTRS{devpath}=="1.4.3"
    ATTRS{idProduct}=="7523"
    ATTRS{idVendor}=="1a86"
    ATTRS{ltm_capable}=="no"
    ATTRS{maxchild}=="0"
    ATTRS{power/active_duration}=="48902765"
    ATTRS{power/autosuspend}=="2"
    ATTRS{power/autosuspend_delay_ms}=="2000"
    ATTRS{power/connected_duration}=="48902765"
    ATTRS{power/control}=="on"
    ATTRS{power/level}=="on"
    ATTRS{power/persist}=="1"
    ATTRS{power/runtime_active_time}=="48902599"
    ATTRS{power/runtime_status}=="active"
    ATTRS{power/runtime_suspended_time}=="0"
    ATTRS{product}=="USB2.0-Serial"
    ATTRS{quirks}=="0x0"
    ATTRS{removable}=="unknown"
    ATTRS{rx_lanes}=="1"
    ATTRS{speed}=="12"
    ATTRS{tx_lanes}=="1"
    ATTRS{urbnum}=="17"
    ATTRS{version}==" 1.10"

[...]
```

In this output, we find that the device itself (at the top) doesn't have any useful attributes we can use for creating a systematic device name. It's not until we've moved up the device hierarchy to `/devices/pci0000:00/0000:00:1c.0/0000:03:00.0/usb3/3-1/3-1.4/3-1.4.3` that we find topology information (in the `busnum` and `devpath` attributes). This complicates matters because a udev rule only has access to attributes defined directly on matching device, so we can't right something like:

```
SUBSYSTEM=="usb-serial", SYMLINK+="usbserial/$attr{busnum}/$attr{devpath}"
```

How do we access the attributes of a parent node in our rule?

The answer is by creating environment variables that preserve the values in which we are interested. I started with this:

```
SUBSYSTEMS=="usb", ENV{.USB_BUSNUM}="$attr{busnum}", ENV{.USB_DEVPATH}="$attr{devpath}"
```

Here, my goal was to stash the `busnum` and `devpath` attributes in `.USB_BUSNUM` and `.USB_DEVPATH`, but this didn't work: it matches device path `/devices/pci0000:00/0000:00:1c.0/0000:03:00.0/usb3/3-1/3-1.4/3-1.4.3/3-1.4.3:1.0`, which is:

```
KERNELS=="3-1.4.3:1.0"
SUBSYSTEMS=="usb"
DRIVERS=="ch341"
ATTRS{authorized}=="1"
ATTRS{bAlternateSetting}==" 0"
ATTRS{bInterfaceClass}=="ff"
ATTRS{bInterfaceNumber}=="00"
ATTRS{bInterfaceProtocol}=="02"
ATTRS{bInterfaceSubClass}=="01"
ATTRS{bNumEndpoints}=="03"
ATTRS{supports_autosuspend}=="1"
```

We need to match the next device up the chain, so we need to make our match more specific. There are a couple of different options we can pursue; the simplest is probably to take advantage of the fact that the next device up the chain has `SUBSYSTEMS=="usb"` and `DRIVERS="usb"`, so we could instead write:

```
SUBSYSTEMS=="usb", DRIVERS=="usb", ENV{.USB_BUSNUM}="$attr{busnum}", ENV{.USB_DEVPATH}="$attr{devpath}"
```

Alternately, we could ask for "the first device that has a `busnum` attribute" like this:

```
SUBSYSTEMS=="usb", ATTRS{busnum}=="?*", ENV{.USB_BUSNUM}="$attr{busnum}", ENV{.USB_DEVPATH}="$attr{devpath}"
```

Where (from the `udev(7)` man page), `?` matches any single character and `*` matches zero or more characters, so this matches any device in which `busnum` has a non-empty value. We can test this rule out using the `udevadm test` command:

```
# udevadm test $(udevadm info --query=path --name=/dev/ttyUSB0)
[...]
.USB_BUSNUM=3
.USB_DEVPATH=1.4.3
[...]
```

This shows us that our rule is matching and setting up the appropriate variables. We can now use those in a subsequent rule to create the desired symlink:

```
SUBSYSTEMS=="usb", ATTRS{busnum}=="?*", ENV{.USB_BUSNUM}="$attr{busnum}", ENV{.USB_DEVPATH}="$attr{devpath}"
SUBSYSTEMS=="usb-serial", SYMLINK+="usbserial/$env{.USB_BUSNUM}/$env{.USB_DEVPATH}"
```

Re-running the test command, we see:

```
# udevadm test $(udevadm info --query=path --name=/dev/ttyUSB0)
[...]
DEVLINKS=/dev/serial/by-path/pci-0000:03:00.0-usb-0:1.4.3:1.0-port0 /dev/usbserial/3/1.4.3 /dev/serial/by-id/usb-1a86_USB2.0-Serial-if00-port0
[...]
```

You can see the new symlink in the `DEVLINKS` value, and looking at `/dev/usbserial` we can see the expected symlinks:

```
# tree /dev/usbserial
/dev/usbserial/
└── 3
    ├── 1.1 -> ../../ttyUSB1
    └── 1.4.3 -> ../../ttyUSB0
```

And there have it. Now as long as I attach a specific device to the same USB port on my system, it will have the same device node. I've updated my tooling to use these paths (`/dev/usbserial/3/1.4.3`) instead of the kernel names (`/dev/ttyUSB0`), and it has greatly simplified things.
