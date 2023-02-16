---
categories:
- tech
date: '2020-12-18'
filename: 2020-12-18-to-sleep-or-not-to-sleep.md
tags:
- python
- micropython
- esp8266
title: To sleep or not to sleep?

---

Let's say you have a couple of sensors attached to an ESP8266 running
[MicroPython][]. You'd like to sample them at different frequencies
(say, one every 60 seconds and one every five minutes), and you'd like
to do it as efficiently as possible in terms of power consumption.
What are your options?

[micropython]: https://micropython.org/

If we don't care about power efficiency, the simplest solution is
probably a loop like this:

```
import machine

lastrun_1 = 0
lastrun_2 = 0

while True:
    now = time.time()

    if (lastrun_1 == 0) or (now - lastrun_1 >= 60):
        read_sensor_1()
        lastrun_1 = now
    if (lastrun_2 == 0) or (now - lastrun_2 >= 300):
        read_sensor_2()
        lastrun_2 = now

    machine.idle()
```

If we were only reading a single sensor (or multiple sensors at the
same interval), we could drop the loop and juse use the ESP8266's deep
sleep mode (assuming we have [wired things properly][]):

[wired things properly]: http://docs.micropython.org/en/latest/esp8266/tutorial/powerctrl.html#deep-sleep-mode

```
import machine

def deepsleep(duration):
    rtc = machine.RTC()
    rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)
    rtc.alarm(rtc.ALARM0, duration)


read_sensor_1()
deepsleep(60000)
```

This will wake up, read the sensor, then sleep for 60 seconds, at
which point the device will reboot and repeat the process.

If we want both use deep sleep *and* run tasks at different intervals,
we can effectively combine the above two methods.  This requires a
little help from the RTC, which in addition to keeping time also
provides us with a small amount of memory (492 bytes when using
MicroPython) that will persist across a deepsleep/reset cycle.

The `machine.RTC` class includes a `memory` method that provides
access to the RTC memory. We can read the memory like this:

```
import machine

rtc = machine.RTC()
bytes = rtc.memory()
```

Note that `rtc.memory()` will always return a byte string.

We write to it like this:

```
rtc.memory('somevalue')
```

Lastly, note that the time maintained by the RTC also persists across
a deepsleep/reset cycle, so that if we call `time.time()` and then
deepsleep for 10 seconds, when the module boots back up `time.time()`
will show that 10 seconds have elapsed.

We're going to implement a solution similar to the loop presented at
the beginning of this article in that we will store the time at which
at task was last run. Because we need to maintain two different
values, and because the RTC memory operates on bytes, we need a way to
serialize and deserialize a pair of integers. We could use functions
like this:

```
import json

def store_time(t1, t2):
  rtc.memory(json.dumps([t1, t2]))

def load_time():
  data = rtc.memory()
  if not data:
    return [0, 0]

  try:
    return json.loads(data)
  except ValueError:
    return [0, 0]
```

The `load_time` method returns `[0, 0]` if either (a) the RTC memory
was unset or (b) we were unable to decode the value stored in memory
(which might happen if you had previously stored something else
there).

You don't have to use `json` for serializing the data we're storing in
the RTC; you could just as easily use the `struct` module:

```
import struct

def store_time(t1, t2):
  rtc.memory(struct.pack('ll', t1, t2))

def load_time():
  data = rtc.memory()
  if not data:
    return [0, 0]

  try:
    return struct.unpack('ll', data)
  except ValueError:
    return [0, 0]
```

Once we're able to store and retrieve data from the RTC, the main part
of our code ends up looking something like this:

```
lastrun_1, lastrun_2 = load_time()
now = time.time()
something_happened = False

if lastrun_1 == 0 or (now - lastrun_1 > 60):
    read_sensor_1()
    lastrun_1 = now
    something_happened = True

if lastrun_2 == 0 or (now - lastrun_2 > 300):
    read_sensor_2()
    lastrun_2 = now
    something_happened = True

if something_happened:
  store_time(lastrun_1, lastrun_2)

deepsleep(60000)
```

This code will wake up every 60 seconds. That means it will always run
the `read_sensor_1` task,  and it will run the `read_sensor_2` task
every five minutes. In between, the ESP8266 will be in deep sleep
mode, consuming around 20µA. In order to avoid too many unnecessary
writes to RTC memory, we only store values when `lastrun_1` or
`lastrun_2` has changed.

While developing your code, it can be inconvenient to have the device
enter deep sleep mode (because you can't just `^C` to return to the
REPL). You can make the deep sleep behavior optional by wrapping
everything in a loop, and optionally calling `deepsleep` at the end of
the loop, like this:

```
lastrun_1, lastrun_2 = load_time()

while True:
    now = time.time()
    something_happened = False

    if lastrun_1 == 0 or (now - lastrun_1 > 60):
        read_sensor_1()
        lastrun_1 = now
        something_happened = True

    if lastrun_2 == 0 or (now - lastrun_2 > 300):
        read_sensor_2()
        lastrun_2 = now
        something_happened = True

    if something_happened:
      store_time(lastrun_1, lastrun_2)

    if use_deep_sleep:
        deepsleep(60000)
    else:
        machine.idle()
```

If the variable `use_deepsleep` is `True`, this code will perform as
described in the previous section, waking once every 60 seconds. If
`use_deepsleep` is `False`, this will use a busy loop.
