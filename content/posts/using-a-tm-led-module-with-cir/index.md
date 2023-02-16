---
categories: [tech]
aliases: ["/2018/05/03/using-a-tm-led-module-with-cir/"]
title: Using a TM1637 LED module with CircuitPython
date: "2018-05-03"
tags:
- python
- esp8266
- circuitpython
- micropython
- adafruit
---

[CircuitPython][] is "an education friendly open source derivative of
[MicroPython][]".  MicroPython is a port of Python to microcontroller
environments; it can run on boards with very few resources such as the
[ESP8266][].  I've recently started experimenting with CircuitPython
on a [Wemos D1 mini][], which is a small form-factor ESP8266 board.

I had previously been using Mike Causer's [micropython-tm1637][] for
MicroPython to drive a [4 digit LED display][tm1637].  I was hoping to
get the same code working under CircuitPython, but when I tried to
build an image that included the `tm1637` module I ran into:

```python
>>> import tm1637
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "tm1637.py", line 6, in <module>
ImportError: cannot import name sleep_us
```

One of CircuitPython's goals is to be as close to CPython as possible.
This means that in many cases the CircuitPython folks have
re-implemented MicroPython modules to have syntax that is more a
strict subset of the CPython equivalent, and the MicroPython `time`
module is impacted by this change.  With stock MicroPython, the `time`
module has:

```python
>>> print('\n'.join(dir(time)))
__class__
__name__
localtime
mktime
sleep
sleep_ms
sleep_us
ticks_add
ticks_cpu
ticks_diff
ticks_ms
ticks_us
time
```

But the corresponding CircuitPython module has:

```python
>>> print('\n'.join(dir(time)))
__name__
monotonic
sleep
struct_time
localtime
mktime
time
```

It turns out that the necessary functions are defined in the `utime`
module, which is implemented by `ports/esp8266/modutime.c`, but this
module is not included in the CircuitPython build. How do we fix that?

The most obvious change is to add `modutime.c` to the `SRC_C` variable
in `ports/esp8266/Makefile`, which gets us:

```
SRC_C = \
        [...]
        modesp.c \
        modnetwork.c \
        modutime.c \
        [...]
```

After making this change and trying to build CircuitPython, I
hit 70 or so lines like:

```
Generating build/genhdr/mpversion.h
In file included from ../../py/mpstate.h:35:0,
                 from ../../py/runtime.h:29,
                 from modutime.c:32:
modutime.c:109:50: error: 'MP_QSTR_utime' undeclared here (not in a function)
     { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_utime) },
                                                  ^
```

The `MP_QSTR_` macros are sort of magical: they are generated during
the build process by scanning for references of the form
`MP_QSTR_utime` and creating definitions that look like this:

```c
QDEF(MP_QSTR_utime, (const byte*)"\xe5\x9d\x05" "utime")
```

But...and this is the immediate problem...this generation only happens
with a clean build.  Running `make clean` and then re-running the
build yields:

```
build/shared-bindings/time/__init__.o:(.rodata.time_localtime_obj+0x0): multiple definition of `time_localtime_obj'
build/modutime.o:(.rodata.time_localtime_obj+0x0): first defined here
build/shared-bindings/time/__init__.o:(.rodata.time_mktime_obj+0x0): multiple definition of `time_mktime_obj'
build/modutime.o:(.rodata.time_mktime_obj+0x0): first defined here
build/shared-bindings/time/__init__.o:(.rodata.time_time_obj+0x0): multiple definition of `time_time_obj'
build/modutime.o:(.rodata.time_time_obj+0x0): first defined here
```

The above errors show a conflict between the structures defined in
`utime`, which have just activated, and the existing `time`
module.  A simple rename will take care of that problem; instead of:

```c
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(time_localtime_obj, 0, 1, time_localtime);
```

We want:

```c
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(utime_localtime_obj, 0, 1, time_localtime);
```

And so forth.  At this point, everything builds correctly, but if we
deploy the image to our board and try to import the `utime` module, we
see:

```python
>>> import utime
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ImportError: no module named 'utime'
```

The final piece of this puzzle is that there is a list of built-in
modules defined in `mpconfigport.h`.  We need to add our `utime`
module to that list:

```c
#define MICROPY_PORT_BUILTIN_MODULES \
    [...]
    { MP_ROM_QSTR(MP_QSTR_utime), MP_ROM_PTR(&utime_module) }, \
    [...]
```

If we build and deploy our image, we're now able to use the methods
from the `utime` module:

```python
Adafruit CircuitPython 3.0.0-alpha.6-42-gb46567004 on 2018-05-06; ESP module with ESP8266
>>> import utime
>>> utime.sleep_ms(1000)
>>>
```

We need to make one final change to the `tm1637` module, since as
written it imports methods from the `time` module.  Instead of:

```python
from time import sleep_us, sleep_ms
```

We have to modify it to read:

```python
try:
    from time import sleep_us, sleep_ms
except ImportError:
    from utime import sleep_us, sleep_ms
```

With our working `utime` module and the modified `tm1637` module, we
are now able to drive our display:

{{< youtube laH7HY-wlCk >}}

[micropython-tm1637]: https://github.com/mcauser/micropython-tm1637/
[esp8266]: https://en.wikipedia.org/wiki/ESP8266
[wemos d1 mini]: https://wiki.wemos.cc/products:d1:d1_mini
[feature/utime]: https://github.com/larsks/micropython/tree/feature/utime
[circuitpython]: https://learn.adafruit.com/welcome-to-circuitpython/overview
[micropython]: https://micropython.org/
[tm1637]: http://a.co/gQVPtPr
