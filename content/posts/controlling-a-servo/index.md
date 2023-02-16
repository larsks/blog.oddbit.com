---
categories: [tech]
aliases: ["/2013/03/07/controlling-a-servo/"]
title: Controlling a servo with your Arduino
date: "2013-03-07"
tags:
  - arduino
  - hardware
---

I've recently started playing with an [Arduino][] kit I purchased a year
ago (and only just now got around to unboxing).  I purchased the kit
from [SparkFun][], and it includes a motley collection of resistors,
LEDs, a motor, a servo, and more.

I was fiddling around with [this exercise][circ04], which uses the
`SoftwareServo` library to control a servo.  Using this library,
you just pass it an angle and the library takes care of everything
else, e.g. to rotate to 90 degrees you would do this:

    myservo.write(90);

The exercise suggests trying to control the servo without using the
library:

> While it is easy to control a servo using the Arduino’s included
> library sometimes it is fun to figure out how to program something
> yourself. Try it. We’re controlling the pulse directly so you could
> use this method to control servos on any of the Arduino’s 20
> available pins (you need to highly optimize this code before doing
> that).

It took me a few tries, and it looks as if the upper and lower limits
for the servo pulses given in that documentation may not be 100%
accurate.  This is what I finally came with.  As an added bonus, it
writes position information to the serial port:

    int incomingByte = 0;
    int servo0 = 600;
    int servo180 = 2100;
    int inc = 20;
    int pos = servo0;
    int servoPin = 9;
    int pulseInterval=2000;

    void setup() {
      Serial.begin(9600);     // opens serial port, sets data rate to 9600 bps
      pinMode(servoPin, OUTPUT);
    }

    void loop() {
      int i;

      pos += inc;

      if (pos > servo180) {
        Serial.println("REVERSE!");
        pos = servo180;
        inc *= -1;
        delay(500);
      } else if (pos < servo0) {
        Serial.println("FORWARD!");
        pos = servo0;
        inc *= -1;
        delay(500);
      }

      Serial.print("pos = ");
      Serial.println(pos, DEC);

      digitalWrite(servoPin, HIGH);
      delayMicroseconds(pos);
      digitalWrite(servoPin, LOW);
      delay(20);
    }

Under Linux or OS X, you could view the serial output using `screen`
like this:

    screen /dev/tty.usbmodemfd12441 9600
    
[sparkfun]: https://www.sparkfun.com/
[circ04]: http://oomlout.com/a/products/ardx/circ-04/
[arduino]: http://arduino.cc/

