---
categories:
- tech
date: '2020-03-20'
filename: 2020-03-20-i-see-you-have-the-machine-tha.md
tags:
- arduino
- esp8266
- micropython
- python
- wifi
title: I see you have the machine that goes ping...
---

We're all looking for ways to keep ourselves occupied these days, and
for me that means leaping at the chance to turn a small problem into a
slightly ridiculous electronics project. For reasons that I won't go
into here I wanted to generate an alert when a certain WiFi BSSID
becomes visible. A simple solution to this problem would have been a
few lines of shell script to send me an email...but this article isn't
about simple solutions!

I thought it would be fun to put together a physical device of some
sort that would sound an alarm when the network in question was
visible. There weren't too many options floating around the house -- I
found a [small buzzer][], but it wasn't very loud so wasn't much use
unless I was right next to it.  I needed something a little more
dramatic, and found it in the old chime doorbell I had floating
around the basement. This means the problem statement became:

[small buzzer]: https://www.amazon.com/RuiLing-Decibels-Continuous-Sounder-Electronic/dp/B07NK8MGL9

> Design a device that will ring the doorbell chime when a given BSSID
> becomes visible.

(Why a BSSID? The BSSID is the hardware address of the access point.
In most cases, it's easy to change the name of a WiFi network -- the
SSID -- but somewhat more difficult to change the BSSID.)

# TL;DR

Before looking at the implementation in more detail, let's take a look
at the finished project. When the device detects a target BSSID, it
rings the bell twice and lights the `ALARM` LED:

{{< youtube cT2JB-aDhTQ >}}

After the initial alarm, the bell will ring once every five minutes
while the alarm persists. Once the BSSID goes offline, the device
cancels the alarm and extinguishes the `ALARM` LED:

{{< youtube XY6YKFK2qv4 >}}

If the doorbell proves annoying, there's a switch that activates
silent mode:

{{< youtube bgM7Asc4FD4 >}}

When silent mode is active, the device will illuminate the `ALARM` LED
without sounding the bell:

{{< youtube xRxxqKiiYVc >}}

## But wait, there's more!

There's also a web interface that allows one to monitor and configure
the device. The web interface allows one to:

- See a list of visible networks
- Add a network to the list of targets
- Remove a network from the list of targets
- See whether or not the scanning "thread" is active
- See whether or not there is currently an active alarm

Here's a video of it in action:

{{< youtube TtDwYMXy-b8 >}}

## And that's not all!

In order to support the UI, there's a simple HTTP API that permits
programmatic interaction with the device. The API supports the
following endpoints:

- `GET /api/target` -- get a list of targets
- `POST /api/target' -- add a BSSID to the list of targets
- `DELETE /api/target/<bssid>` -- remove a BSSID from the list of
  targets
- `GET /api/status` -- get the current alarm status and whether or not
  the scan is running
- `GET /api/scan/result` -- get list of visible networks
- `GET /api/scan/start` -- start the scan
- `GET /api/scan/stop` -- stop the scan

There are a couple of other methods, too, but they're more for
debugging than anything else.

## Show me the code!

The code for this project is all online at
<https://github.com/larsks/maxdetector>.

# Implementation details

## Software notes

My initial inclination was to implement the entire solution in
[MicroPython][] on an [Wemos D1 mini][] (an [esp8266][] development
board), but this proved problematic: MicroPython's `network.WLAN.scan`
method is a blocking operation, by which I mean it blocks
*everything*, including interrupt handling, timer tasks, etc.  This
made it difficult to handle some physical UI aspects, such as button
debouncing, in a reliable fashion.

[micropython]: https://micropython.org/
[esp8266]: https://en.wikipedia.org/wiki/ESP8266
[wemos d1 mini]: https://docs.wemos.cc/en/latest/d1/d1_mini.html

I ended up moving the physical UI aspects to an [Arduino Uno][]. The
ESP8266 handles scanning for WiFi networks, and raises a signal to the
Uno when an alarm is active. The Uno handles the silent mode button,
the LEDs, and the relay attached to the doorbell.

[arduino uno]: https://store.arduino.cc/usa/arduino-uno-rev3

After the initial implementation, I realized that it really need a web
interface (because of course it does), so in addition to the WiFi
scanning the ESP8266 now hosts a simple web server. Because of the
blocking nature of the WiFi scan, this means the web server may
occasionally pause for a few seconds, but this hasn't proven to be a
problem.

In the end, I have four major blocks of code in three different languages:

- [maxdetector.py](https://github.com/larsks/maxdetector/blob/master/maxdetector.py) implements the WiFi scanning
- [server.py](https://github.com/larsks/maxdetector/blob/master/server.py) implements the server side of the web interface
- [md.js](https://github.com/larsks/maxdetector/blob/master/static/md.js) implements the dynamic portion of the web interface
- [maxdetector.cpp](https://github.com/larsks/maxdetector/blob/master/src/maxdetector.cpp) implements the physical UI and operates the doorbell

### Wifi scanning

The WiFi scanning operation is implemented as a "background task"
driven by a MicroPython [virtual timer][]. The scanning task triggers
once every 10 seconds (and takes a little over 2 seconds to complete).

[virtual timer]: https://docs.micropython.org/en/latest/esp8266/quickref.html#timers

### Web server

The web server is a simple `select.poll()` based server capable of
servicing multiple clients (very, very slowly). I was interested in an
`asyncio` implementation, but at the time the only `asyncio`
module for MicroPython was the one in [micropython-lib][], which
hadn't been touched in several years. A new `asyncio` module has
recently been [added to micropython][], but that post-dates the
implementation of this project.

[micropython-lib]: https://github.com/micropython/micropython-lib
[added to micropython]: https://github.com/micropython/micropython/commit/1d4d688b3b251120f5827a3605ec232d977eaa0f

The server uses a very simple route-registration mechanism that should
be familiar if you've worked with various other Python web frameworks.
It would be relatively easy to repurpose it for something other than
this project.

## The hardware

Everything is bundled "neatly" (whereby "neatly" I mean "haphazardly")
into an old shoe box. On the outside, you can see the three LEDs (for
the ACTIVE, SILENT, and ALARM signals), the SILENT switch, and the
doorbell itself:

{{< figure src="detector-outside-labelled.png" >}}

On the inside, you'll find the Arduino Uno, the Wemos D1 mini, the
relay, and a step-down converter:

{{< figure src="detector-inside-labelled.png" >}}

The step-down converter isn't actually necessary: when I put things
together, I didn't realize that the Uno would accept up to 12V into
its regulator. Since I already had the step-down converter in place,
I'm feeding about 7.5v to the Uno. The doorbell gets 12V.

I initially prototyped the circuit in [Tinkercad Circuits][], where
everything worked just fine. But after wiring things up and testing out
the device, it would start ringing endlessly. Upon inspection, this
was because the Uno was resetting every time the doorbell chimed. This
was due to flyback voltage from the relay, which is simple to fix if
you happen to have an appropriate diode handy...but if you don't, it
means calling around to all your aquaintenances to find someone who
happens to have some lying around. With a diode in place, everything
worked swimmingly.

[tinkercad circuits]: https://www.tinkercad.com/things/cpRuevAoV5L-max-detector
