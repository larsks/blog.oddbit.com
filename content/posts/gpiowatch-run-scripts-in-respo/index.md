---
categories: [tech]
aliases: ["/2014/07/26/gpiowatch-run-scripts-in-respo/"]
title: "gpio-watch: Run scripts in response to GPIO signals"
date: "2014-07-26"
tags:
  - raspberrypi
  - gpio
---

For a small project I'm working on I needed to attach a few buttons to
a [Raspberry Pi][] and have some code execute in response to the
button presses.

[raspberry pi]: http://raspberrypi.org/

Normally I would reach for [Python][] for a simple project like this,
but constraints of the project made it necessary to implement
something in C with minimal dependencies.  I didn't want to write
something that was tied closely to my project...

<!-- more -->

[python]: http://python.org/

{{< figure
link="https://xkcd.com/974/"
src="http://imgs.xkcd.com/comics/the_general_problem.png"
>}}

...so I ended up writing [gpio-watch][], a simple tool for connecting
shell scripts (or any other executable) to GPIO events.  There are a
few ways to interact with GPIO on the Raspberry Pi.  For the fastest
possible performance, you will need to interact directly with the
underlying hardware using, e.g., something like [direct register
access][dra].  Since I was only responding to button presses I opted
to take advantage of the [GPIO sysfs interface][sysfs], which exposes
the GPIO pins via the filesystem.

[gpio-watch]: https://github.com/larsks/gpio-watch
[dra]: http://hertaville.com/2014/07/07/rpimmapgpio/
[sysfs]: https://www.kernel.org/doc/Documentation/gpio/sysfs.txt

To access a GPIO pin using the `sysfs` interface:

- You write the GPIO number to `/sys/class/gpio/export`.  This will
  result in a new directory named `gpio<pin>` appearing in
  `/sys/class/gpio` (where `<pin>` is the GPIO number you have exported).

- Inside `/sys/class/gpio/gpio<pin>`, there are a number of files:

  - `direction` is used to configure the GPIO as an input (write `in`)
    or output (write `out`).
  - `edge` is used to control which edge of a signal generates
    interrupts.  The options are `rising`, `falling`, `both`, or
    `none`.
  - `value` contains the current value of the GPIO pin.

- Once you have properly configure a pin, you can monitor the `value`
  file for events (see below).

We can use the `poll()` or `select()` system calls to monitor events
on `/sys/class/gpio/gpio<pin>/value`.  For example, to wait for a signal
on GPIO 23 (assuming that we have correctly configured the `direction`
and `edge` values):

    #include <poll.h>
    #include <fcntl.h>
    #include <stdio.h>

    void poll_pin() {
      struct pollfd fdlist[1];
      int fd;

      fd = open("/sys/class/gpio/gpio23/value", O_RDONLY);
      fdlist[0].fd = fd;
      fdlist[0].events = POLLPRI;

      while (1) {
        int err;
        char buf[3];

        err = poll(fdlist, 1, -1);
        if (-1 == err) {
          perror("poll");
          return;
        }

        err = read(fdlist[0].fd, buf, 2);
        printf("event on pin 23!\n");
      }
    }

    int main(int argc, char *argv[]) {
      poll_pin();
    }

The `gpio-watch` command wraps this all up in a convenient package
that lets you do something like this:

    gpio-watch -e rising 18 23 24

The `-e rising` option means that we are watching for rising signals
on all three pins.  You can also trigger on different parts of the
signal for each pin:
    gpio-watch 18:rising 23:both 24:falling

When `gpio-watch` sees an event on a pin, it looks for
`/etc/gpio-scripts/<pin>` (e.g., `/etc/gpio-scripts/23`), and then runs:

    /etc/gpio-scripts/<pin> <pin> <value>

Since the script is passed the pin number as the first argument, you
can use a single script to handle events on multiple pins (by
symlinking the script to the appropriate name).

## Mechanical switches

There is some special code in `gpio-watch` for handling mechanical
buttons.  The `switch` edge mode...

    gpio-watch 23:switch

...enables some simple [de-bouncing][] logic.  This causes
`gpio-watch` to monitor both rising and falling events on this pin,
but the events scripts will only trigger on the falling edge event,
which must occur more than `DEBOUNCE_INTERVAL` after the rising edge
event.  In other words, you must both press and release the button for
the event to fire, and the debounce logic should avoid firing the
event multiple times due to contact bounce.

[de-bouncing]: https://en.wikipedia.org/wiki/Switch#Contact_bounce

As an example, assume we have a script `/etc/gpio-scripts/23` that
looks like this:

    #!/bin/sh

    echo "Something happened! Pin=$1, value=$2"

If I run `gpio-watch` to monitor the falling signal edge and press a
button attached to pin 23 three times, I see:

    $ gpio-watch 23:falling
    Something happened! Pin=23, value=0
    Something happened! Pin=23, value=0
    Something happened! Pin=23, value=0
    Something happened! Pin=23, value=1
    Something happened! Pin=23, value=0

Whereas if I use `switch` mode, I see:

    $ gpio-watch 23:switch
    Something happened! Pin=23, value=0
    Something happened! Pin=23, value=0
    Something happened! Pin=23, value=0

## Use the source, Luke!

The source is available [on gitub][gpio-watch].  To get started, clone
the repository with `git`:

    $ git clone https://github.com/larsks/gpio-watch.git

And then build the source using `make`:

    $ cd gpio-watch
    $ make
    cc    -c -o main.o main.c
    cc    -c -o gpio.o gpio.c
    cc    -c -o fileutil.o fileutil.c
    cc    -c -o logging.o logging.c
    cc  -o gpio-watch main.o gpio.o fileutil.o logging.o -lrt

There is basic documentation in `README.md` in the distribution.  If
you run into any problems, feel free to [open a new issue][newissue].

[newissue]: https://github.com/larsks/gpio-watch/issues/new

