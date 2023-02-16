---
categories: [tech]
aliases: ["/2013/03/12/i2c-on-the-raspberry/"]
title: I2C on the Raspberry Pi
date: "2013-03-12"
tags:
  - hardware
  - raspberrypi
  - arduino
  - i2c
---

I've set up my [Raspberry Pi][] to communicate with my [Arduino][] via
[I2C][].  The Raspberry Pi is a 3.3v device and the Arduino is a 5v
device.  While in general this means that you need to use a level
converter when connecting the two devices, **you don't need to use a
level converter when connecting the Arduino to the Raspberry Pi via
I2C.** 

The design of the I2C bus is such that the only device driving a
voltage on the bus is the master (in this case, the Raspberry Pi), via
pull-up resistors.  So when "idle", the bus is pulled to 3.3v volts by
the Pi, which is perfectly safe for the Arduino (and compatible with
it's 5v signaling).  To transmit data on the bus, a device brings the
bus low by connecting it to ground.  In other words, slave devices
*never* drive the bus high.  This means that the Raspberry Pi will
never see a 5v signal from the Arduino...unless, of course, you make a
mistake and accidentally `digitalWrite` a `HIGH` value on one of the
Arduino's `I2C` pins.  So don't do that.

Note that the built-in pull-up resistors are *only* available on the
Pi's I2C pins (Pins 3 (`SDA`) and 5 (`SCL`), aka BCM `GPIO0` and
`GPIO1` on a Rev. 1 board, `GPIO2` and `GPIOP3` on a Rev. 2 board):

![Raspberry Pi Pins][]

On the Arduino Uno, the `I2C` pins are pins `A4` (`SDA`) and `A5`
(`SCL`):

![Arduino Uno Pins][]

For information about other boards and about the Arduino I2C API, see
the documentation for the [Wire library][wire].

[raspberry pi]: http://www.raspberrypi.org/
[arduino]: http://www.arduino.cc/
[i2c]: http://en.wikipedia.org/wiki/I%C2%B2C
[pins]: https://projects.drogon.net/raspberry-pi/wiringpi/special-pin-functions/
[wire]: http://arduino.cc/en/Reference/Wire

[arduino uno pins]: arduino-i2c-pins.jpg
[raspberry pi pins]: raspberry-pi-i2c-pins.jpg

