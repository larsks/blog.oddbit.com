---
categories: [tech]
title: "Avoiding personal hotspot bandwidth limiting using tinyproxy"
date: "2025-01-20"
tags:
  - iphone
  - proxy
  - mobile
---

My cell phone provider caps the amount of data you can receive at high speed using the "personal hotspot" feature of your phone to a few GB/month. This cap only impacts devices using your phone as a hotspot -- there are no caps when using your phone directly. A recent confluence of events -- a week of work travel following a few days of problems with our home internet service -- meant that I ended up burning through the hotspot data cap while still needing to use the phone as hotspot. After you hit the cap, bandwidth is limited to about 600Kbps, which while plenty fast for basic browsing doesn't work all that great for things like videoconferencing.

## Install ish

1. Install [ish] from the app store and start the app; you'll find yourself at a shell prompt. 
2. Towards the bottom of the screen, above the keyboard, you'll see a gear icon; click on this to open the settings.
3. Enable "Keep Screen Turned On". Otherwise, you'll get disconnected whenever your screen turns off.

## Install tinyproxy (and sshd)

```
apk add tinyproxy openssh
```

## Start sshd

First, generate the necessary hostkeys:

```
ssh-keygen -A
```

And then start `sshd`:

```
/usr/sbin/sshd
```

## Configure tinyproxy

```
cat > /etc/tinyproxy/tinyproxy.conf <<EOF
User nobody
Group nobody
Port 8888
Timeout 600
DefaultErrorFile "/usr/share/tinyproxy/default.html"
StatFile "/usr/share/tinyproxy/stats.html"
LogLevel Info
PidFile "/var/run/tinyproxy.pid"
MaxClients 100
Allow 127.0.0.1
Allow ::1
Allow 172.20.10.0/28
ViaProxyName "tinyproxy"
EOF
```

## Running the proxy in the background

```
tinyproxy -d < /dev/location &
```

[ish]: https://ish.app/
[tinyproxy]: https://tinyproxy.github.io/
