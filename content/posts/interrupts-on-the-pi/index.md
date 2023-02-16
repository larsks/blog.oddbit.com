---
categories: [tech]
aliases: ["/2013/08/05/interrupts-on-the-pi/"]
title: Interrupts on the PiFace
date: "2013-08-05"
tags:
  - raspberrypi
  - python
  - piface
---

I recently acquired both a [Raspberry Pi][] and a [PiFace][] IO board.
I had a rough time finding examples of how to read the input ports via
interrupts (rather than periodically polling for values), especially
for the [newer versions][] of the PiFace python libraries.

[newer versions]: https://github.com/piface

After a little research, [here's][buttons.py] some simple code that
will print out pin names as you press the input buttons.  Button 3
will cause the code to exit:

    #!/usr/bin/python

    import pifacecommon.core
    import pifacecommon.interrupts
    import os
    import time

    quit = False

    def print_flag(event):
        print 'You pressed button', event.pin_num, '.'

    def stop_listening(event):
        global quit
        quit = True

    pifacecommon.core.init()

    # GPIOB is the input ports, including the four buttons.
    port = pifacecommon.core.GPIOB

    listener = pifacecommon.interrupts.PortEventListener(port)

    # set up listeners for all buttons
    listener.register(0, pifacecommon.interrupts.IODIR_ON, print_flag)
    listener.register(1, pifacecommon.interrupts.IODIR_ON, print_flag)
    listener.register(2, pifacecommon.interrupts.IODIR_ON, print_flag)
    listener.register(3, pifacecommon.interrupts.IODIR_ON, stop_listening)

    # Start listening for events.  This spawns a new thread.
    listener.activate()

    # Hang around until someone presses button 3.
    while not quit:
        time.sleep(1)

    print 'you pressed button 3 (quitting)'
    listener.deactivate()

[buttons.py]: https://gist.github.com/larsks/6161684
[raspberry pi]: http://www.raspberrypi.org/
[piface]: http://www.element14.com/community/docs/DOC-52857/l/piface-digital-for-raspberry-pi

