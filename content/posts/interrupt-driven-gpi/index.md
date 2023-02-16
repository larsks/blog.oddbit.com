---
categories: [tech]
aliases: ["/2013/03/08/interrupt-driven-gpi/"]
title: Interrupt driven GPIO with Python
date: "2013-03-08"
tags:
  - raspberrypi
  - hardware
---

There are several Python libraries out there for interacting with the
[GPIO][] pins on a Raspberry Pi:

- [RPi.GPIO][] 
- The [WiringPi][] bindings for Python, and
- The [Quick2Wire][] Python API (which depends on Python 3)

All of them are reasonably easy to use, but the Quick2Wire API
provides a uniquely useful feature: `epoll`-enabled GPIO interrupts.
This makes it trivial to write code that efficiently waits for and
responds to things like button presses.

The following simple example waits for a button press attached to
`GPIO1` (but refer to the chart in [this document][pins] to see
exactly what that means; this is pin 12 on a Raspberry Pi v2 board)
and lights an LED attached to `GPIO0` when the button is pressed:

    #!/usr/bin/env python3

    import select
    from quick2wire.gpio import pins, In, Out, Rising, Falling, Both

    button1 = pins.pin(0, direction=In, interrupt=Both)
    led = pins.pin(1, direction=Out)

    with button1,led:
        epoll = select.epoll()
        epoll.register(button1, select.EPOLLIN|select.EPOLLET)
        while True:
            events = epoll.poll()
            for fileno, event in events:
                if fileno == button1.fileno():
                    print('BUTTON 1!', button1.value)
                    led.value = button1.value

There is also a `Selector` class that makes the `epoll` interface a
little easier to use.  The following code is equivalent to the above
`epoll` example:

    #!/usr/bin/env python3

    from quick2wire.gpio import pins, In, Out, Both
    from quick2wire.selector import Selector

    button1 = pins.pin(0, direction=In, interrupt=Both)
    led = pins.pin(1, direction=Out)

    with button1, led, Selector(1) as selector:
        selector.add(button1)
        while True:
            selector.wait()
            if selector.ready == button1:
                print('BUTTON 1!', button1.value)
                led.value = button1.value

The `selector` module includes a `Timer` class that lets you add
one-shot or repeating timers to a `Selector`.  The following example
will light the LED for one second after the button is pressed, unless
the button is pressed again, in which case the LED will go out
immediately:

    #!/usr/bin/env python3

    from quick2wire.gpio import pins, In, Out, Both
    from quick2wire.selector import Selector, Timer

    button1 = pins.pin(0, direction=In, interrupt=Both)
    led = pins.pin(1, direction=Out)
    active = False

    with button1, led, \
            Selector(1) as selector, \
            Timer(offset=2) as timer:

        selector.add(button1)
        selector.add(timer)

        while True:
            selector.wait()
            if selector.ready == button1:
                print('BUTTON 1!', button1.value, active)

                if button1.value:
                    if active:      
                        active = False      
                        led.value = 0       
                        timer.stop()        
                    else:           
                        active = True       
                        led.value = 1       
                        timer.start()       

            if selector.ready == timer:
                if active:  
                    active = False  
                    led.value = 0   

All of these examples rely on Python's [with statement][].  If you're
unfamiliar with `with`, you can find more information [here][with
statement].

[rpi.gpio]: https://pypi.python.org/pypi/RPi.GPIO
[wiringpi]: https://github.com/WiringPi/WiringPi-Python
[quick2wire]: https://github.com/quick2wire/quick2wire-python-api
[pins]: https://projects.drogon.net/raspberry-pi/wiringpi/pins/
[gpio]: https://en.wikipedia.org/wiki/General_Purpose_Input/Output
[with statement]: http://docs.python.org/3/reference/compound_stmts.html#the-with-statement

