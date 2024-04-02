---
categories:
- tech
date: '2020-02-24'
filename: 2020-02-24-a-passwordless-serial-console.md
tags:
- raspiberrypi
- serial
title: A passwordless serial console for your Raspberry Pi
---

`legendre` on `#raspbian` asked:

> How can i config rasp lite to open a shell on the serial uart on boot? Params
> are 1200-8-N-1 Dont want login running, just straight to sh

In this article, we'll walk through one way of implementing this configuration.

## Activate the serial port

Raspberry Pi OS automatically starts a [`getty`][getty] on the serial port if one is available. You should see an `agetty` process associated with your serial port when you run `ps -ef`. For example:

[getty]: https://en.wikipedia.org/wiki/Getty_(Unix)

```
root@raspberrypi:/etc/systemd/system# ps -fe | grep agetty | grep ttyS0
root      1138     1  0 00:24 ttyS0    00:00:00 /sbin/agetty -o -p -- \u --keep-baud 115200,38400,9600 ttyS0 vt220
```

If you don't see this process and you're on a Raspberry Pi 3 (or later), you may need to [explicitly enable the serial port][1] by adding `enable_uart=1` to `/boot/firmware/config.txt`. If you make this change, reboot your Pi before continuing, then repeat the above test to make sure things are working as expected.

Note that your serial port may not always be named `ttyS0`. I'm going to use the value `ttyS0` throughout this article to represent the appropriate device name. The correct device name is the penultimate argument in the above `agetty` command.

## Modify the serial-getty@ttyS0 unit

The `agetty` process we saw in the previous section is started by the `serial-getty@ttyS0.service` service unit (which is an instance of the `serial-getty@.service` [template unit][]). We need to modify that service so that it will call `agetty` with the `--autologin root` option.

[template unit]: https://fedoramagazine.org/systemd-template-unit-files/

Rather than directly editing the unit file `/lib/systemd/system/serial-getty@.service`, we're going to make the changes by creating a systemd "drop-in" configuration to override the stock service unit.  From the [systemd.unit man page][]:

[systemd.unit man page]: https://www.freedesktop.org/software/systemd/man/systemd.unit.html

> Along with a unit file foo.service, a "drop-in" directory foo.service.d/ may exist. All files with the suffix ".conf" from this directory will be parsed after the unit file itself is parsed. This is useful to alter or add configuration settings for a unit, without having to modify unit files.

The easiest way to creating a drop-in unit is with the `systemctl edit` command:

```
systemctl edit serial-getty@ttyS0
```

This will bring up an editor (`nano` by default, unless you have set `VISUAL` in your environment to point at a different editor) for `/etc/systemd/system/serial-getty@ttyS0.d/override.conf` in which you will place your override configuration.

Enter the following content:

```
[Service]
ExecStart=
ExecStart=/sbin/agetty -o '-p -- \u' --keep-baud 115200,38400,9600 --noclear --autologin root ttyS0 vt220
```

(While the original request referenced at the beginning of this post was for a getty running at 1200 bps, the above configuration is more generally useful. To allow connections at 1200 bps, modify the list of rates above to looking something like `115200,38400,9600,1200` (if you want to permit connections at higher speeds) or just `1200` (if you really want to permit only 1200 bps connections).

Save the file, then reload `systemd` by running `systemctl daemon-reload`. This tells `systemd` to re-read its unit files.

Finally, restart the `serial-getty@ttys0` service:

```
systemctl restart serial-getty@ttyS0
```

## Configure passwordless root login on the console

With the above change to the service unit, `agetty` will attempt to log in the `root` user on the console but will prompt for a password. That looks like:

```
Raspbian GNU/Linux 10 raspberrypi ttyS0

raspberrypi login: root (automatic login)

Password:
```

We need to configure things such that the `root` user does not require a password when logging on the serial console. We'll do this by modifying the [PAM][] configuration for the `login` program.

[PAM]: http://www.linux-pam.org/

Add the following to the top of `/etc/pam.d/login`:

```
auth sufficient pam_listfile.so item=tty sense=allow file=/etc/securetty onerr=fail apply=root
```

This configures `login` to permit a login for the `root` user if it finds the login tty in the file `/etc/securetty`.

Now, add the serial port device to `/etc/securetty`:

```
root@raspberrypi:/etc# echo /dev/ttyS0 > /etc/securetty
```

These changes will take affect as soon as `agetty` restarts. You can wait for the `Password:` prompt to timeout, or just restart the service by running `systemctl restart serial-getty@ttyS0`.

---

With these changes, the Pi will now automatically start a `root` shell on the serial port without prompting for a password:

```
Raspbian GNU/Linux 10 raspberrypi ttyS0

raspberrypi login: root (automatic login)

Last login: Mon Feb 24 00:29:00 EST 2020 on ttyS0
Linux raspberrypi 4.19.97-v7+ #1294 SMP Thu Jan 30 13:15:58 GMT 2020 armv7l

[...]

root@raspberrypi:~#

```

[1]: https://www.raspberrypi.org/forums/viewtopic.php?f=28&t=141195
