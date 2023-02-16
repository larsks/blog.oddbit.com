---
categories: [tech]
aliases: ["/2019/01/22/debugging-attiny-code-pt-2/"]
title: "Debugging attiny85 code, part 2: Automating GDB with scripts"
date: "2019-01-22"
seq: 2
tags:
- "attiny85"
- "avr"
- "gdb"
- "simavr"
---

This is the second of three posts about using `gdb` and `simavr` to debug AVR code. The complete series is:

- [Part 1: Using GDB][pt1]

    A walkthrough of using GDB to manually inspect the behavior of our code.

- [Part 2: Automating GDB with scripts][pt2]

    Creating GDB scripts to automatically test the behavior of our code.

- [Part 3: Tracing with simavr][pt3]

    Using `simavr` to collect information about the state of microcontroller pins while our code is running.

[pt1]: {{< ref "debugging-attiny-code-pt-1" >}}
[pt2]: {{< ref "debugging-attiny-code-pt-2" >}}
[pt3]: {{< ref "debugging-attiny-code-pt-3" >}}

## Prerequisites

In these posts, I will be referencing the code from my [pipower][] project that I discussed in [an earlier post][pipower-post]. If you want to follow along, start by cloning that repository:

[pipower]: https://github.com/larsks/pipower

    git clone https://github.com/larsks/pipower

You'll also want to be familiar with the [attiny85][] or a similar AVR microcontroller, since I'll be referring to register names (like `PORTB`) without additional explanation.

[attiny85]: https://www.microchip.com/wwwproducts/en/ATtiny85

## Goals

In [the first post][pt1] on this topic, we looked at how one can use `gdb` and [simavr][] to debug your attiny85 (or other AVR code) without flashing it to a device. In this post, I would like to extend that by looking at how we can automate some aspects of the debugging process.

[simavr]: https://github.com/buserror/simavr

## Sending commands to gdb

In the previous post, we were entering commands into `gdb` manually. It is also possible to provide `gdb` with a script of commands to execute. Let's assume we have a file that contains the following commands:

    file pipower.elf
    target remote :1234
    load

There are a few different mechanisms available for passing these commands to `gdb`. Naively we can simply redirect `stdin`:

    $ avr-gdb < commands.gdb
    GNU gdb (GDB) 8.1
    [...]
    (gdb) Reading symbols from pipower.elf...done.
    (gdb) Remote debugging using :1234
    0x00000000 in __vectors ()
    (gdb) Loading section .text, size 0xa54 lma 0x0
    Loading section .data, size 0x6 lma 0xa54
    Start address 0x0, load size 2650
    Transfer rate: 1293 KB/sec, 31 bytes/write.
    (gdb) quit
    A debugging session is active.

            Inferior 1 [Remote target] will be detached.

    Quit anyway? (y or n) [answered Y; input not from terminal]
    Detaching from program: /home/lars/projects/pipower/sim/pipower.elf, Remote target

This will work fine in situations in which you expect `gdb` to run with no user interaction, but in this particular example, that makes our command file useless: while `gdb` does connect to `simavr`, it then exits immediately. This is where the `--command` (or `-x`) options comes in handy: that will read commands from a file and then return to the `(gdb)` prompt:

    $ avr-gdb -x commands.gdb
    GNU gdb (GDB) 8.1
    [...]
    0x00000000 in __vectors ()
    Loading section .text, size 0xa54 lma 0x0
    Loading section .data, size 0x6 lma 0xa54
    Start address 0x0, load size 2650
    Transfer rate: 1293 KB/sec, 31 bytes/write.
    (gdb)

This allows us to preload our debugging session with commands and then continue with an interactive session. You can achieve something similar using the `source` command in `gdb`:

    $ avr-gdb
    GNU gdb (GDB) 8.1
    [...]
    (gdb) source commands.gdb
    0x00000000 in __vectors ()
    Loading section .text, size 0xa54 lma 0x0
    Loading section .data, size 0x6 lma 0xa54
    Start address 0x0, load size 2650
    Transfer rate: 431 KB/sec, 31 bytes/write.
    (gdb)

## Conditional and temporary breakpoints

There are several different ways to set breakpoints in `gdb`. The simplest is the `b` command, which sets a breakpoint at the given location. This simple breakpoint will trigger whenever execution reaches the given line of code. We can influence this behavior by setting a breakpoint condition, such as:

    b loop if state == STATE_POWEROFF2

This breakpoint will only trigger if the expression (`state == STATE_POWEROFF2`) evaluates to true.

Sometimes, we don't want a persistent breakpoint: we want the code to stop once at a given point, and then continue executing afterwards without stopping again at the same place.  We can accomplish this by setting a temporary breakpoint using the `tb` command.  If we were to write the previous example like this...

    tb loop if state == STATE_POWEROFF2

...then the code would stop *once* at the given breakpoint, but subsequently iterations of the loop would continue merrily on their way.

## Defining new commands

The `gdb` scripting language permits us to create new commands with the `define` command. In the previous post, I simulated the passage of time by iterating through the main loop using a command such as `c 100`. This works, but isn't particularly accurate and may make it difficult if one wants to run for a specific amount of time (for example, to run out a timer). We can define a new `wait_for` command that will let us wait for a given number of milliseconds:

    # wait for <n> milliseconds
    define wait_for
        disable 1
        set $start_time = now
        tb loop if now == $start_time + $arg0
        c
        enable 1
    end

The `disable 1` at the beginning is disabling breakpoint 1, which we assume is the breakpoint created by running `b loop` as in the [previous post][pt1]. We re-enable the breakpoint at the end of the definition.

This takes advantage of the fact that the code in `pipower.c` is explicitly updating a variable call `now` with the output of the `millis()` command, which counts milliseconds since the microprocessor started. We can store the current value of that variable in a `gdb` variable by using the `set` command:

    set $start_time = now

This allows us to create a temporary breakpoint with a break condition that makes use of that value: 

    tb loop if now == $start_time + $arg0

This breakpoint will activate when the global `now` variable is equal to the value we saved in `$start_time` + whatever was passed as an argument to the `wait_for` command.

Since commands can call other commands, we can use the new `wait_for` command to create a new command that simulates a button press. For our purposes, a "button press" means that `PIN_POWER` goes low for 100ms and then goes high. We can simulate that like this:

		define short_press
				set PINB=PINB & ~(1<<PIN_POWER)
				wait_for 100
				set PINB=PINB | 1<<PIN_POWER
				c
		end

Recall that `c` means `continue`, which will cause the code to continue running until it hits a breakpoint.

## Automated testing: the script

Using everything discussed above, we can put together something like the [simulate.gdb][] script included in the `sim` directory of the Pipower project.

[simulate.gdb]: https://github.com/larsks/pipower/tree/master/sim/simulate.gdb

We start by disabling pagination. This prevent `gdb` from stopping and asking us to "press return to continue".

    set pagination off

We load our binary and connect to the simulator:

    file pipower.elf
    target remote :1234
    load

Next, we define a few helper functions to avoid repetitive code in the rest of the script:

    ##
    ## Helper functions
    ##

    # wait for <n> milliseconds
    define wait_for
        disable 1
        set $start_time = now
        tb loop if now == $start_time + $arg0
        c
        enable 1
    end

    # simulate a short press of the power button
    define short_press
        set PINB=PINB & ~(1<<PIN_POWER)
        wait_for 100
        set PINB=PINB | 1<<PIN_POWER
        c
    end

    # log a message
    define log
      printf "\n* %s\n", $arg0
    end

    # run until we reach the given state
    define run_until_state
        disable 1
        tb loop if $arg0 == state
        c
        enable 1
    end

Prior to running the code, we a breakpoint on the `loop()` function:

    ##
    ## Execution starts here
    ##

    # set an initial breakpoint at the start of loop() and advance the program
    # to that point
    b loop

And then start things running.  This will stop at the top of `loop()`:

    c

In order to see how things are progressing as the script runs, let's arrange to display the current value of the global `state` variable as well as the `PORTB` and `PINB` registers every time we hit a breakpoint:

    # set up some information to display at each breakpoint
    display state
    display /t PORTB
    display /t PINB
    display

Now that our displays are setup, let's run the code for a bit and then set `PIN_USB` high (this would indicate that external power is available to our device):

    # let the code advance for 100ms
    wait_for 100

    # enable external power
    log "setting PIN_USB"
    set PINB=PINB | 1<<PIN_USB

We'll use the `run_until_state` command that we defined earlier in the file to execute until we reach the `STATE_BOOTWAIT1` state:

    run_until_state STATE_BOOTWAIT1
    wait_for 100

At this point, the code expects an attached Raspberry Pi to assert the `BOOT` signal by bringing `PIN_BOOT` low:

    # assert BOOT
    log "resetting PIN_BOOT"
    set PINB=PINB & ~(1<<PIN_BOOT)
    run_until_state STATE_BOOT

Once the Pi has booted successfully and provided the `BOOT` signal to our code, we enter the `STATE_BOOT` state.  Let's run in this state for a second...

    ##
    ## ...the pi has booted...
    ##
    wait_for 1000

...and then simulate a press of the power button:

    # request a shutdown by pressing the power button
    log "pressing power button"
    short_press

Our code sets `PIN_SHUTDOWN` high, which would signal to an attached Pi that it should begin the shutdown process.  The code enters the `STATE_SHUTDOWN1` state in which it waits for the Pi to signal successful shutdown by de-asserting `BOOT` by bringing `PIN_BOOT` high:

    run_until_state STATE_SHUTDOWN1

    # de-assert BOOT
    wait_for 100
    log "setting PIN_BOOT"
    set PINB=PINB | 1<<PIN_BOOT

Once we receive the successful shutdown signal, the code enters the poweroff phase, during which it will wait `TIMER_POWEROFF` milliseconds before cutting the power.  Let's walk through the poweroff state transitions:

    # step through state transitions until we reach
    # STATE_IDLE2
    run_until_state STATE_POWEROFF0
    run_until_state STATE_POWEROFF1
    run_until_state STATE_POWEROFF2
    log "entering idle mode"
    run_until_state STATE_IDLE0
    run_until_state STATE_IDLE1
    run_until_state STATE_IDLE2

    wait_for 100

And finally force the code to exit:

    log "setting quit flag"
    set state=STATE_QUIT
    finish

    disconnect
    quit

## Automated testing: the output

Running that script produces the following output, which lets us see the state transitions and pin values as the code is running:

    0x00000000 in __vectors ()
    Loading section .text, size 0xa74 lma 0x0
    Loading section .data, size 0x6 lma 0xa74
    Start address 0x0, load size 2682
    Transfer rate: 873 KB/sec, 31 bytes/write.
    Breakpoint 1 at 0xb0: file ../pipower.c, line 116.

    Breakpoint 1, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_START
    2: /t PORTB = 10001
    3: /t PINB = 10001
    Temporary breakpoint 2 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 2, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_IDLE2
    2: /t PORTB = 10001
    3: /t PINB = 10001

    * setting PIN_USB
    Temporary breakpoint 3 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 3, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_BOOTWAIT1
    2: /t PORTB = 10101
    3: /t PINB = 10111
    Temporary breakpoint 4 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 4, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_BOOTWAIT1
    2: /t PORTB = 10101
    3: /t PINB = 10111

    * resetting PIN_BOOT
    Temporary breakpoint 5 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 5, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_BOOT
    2: /t PORTB = 10101
    3: /t PINB = 111
    Temporary breakpoint 6 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 6, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_BOOT
    2: /t PORTB = 10101
    3: /t PINB = 111

    * pressing power button
    Temporary breakpoint 7 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 7, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_BOOT
    2: /t PORTB = 10101
    3: /t PINB = 110

    Breakpoint 1, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_BOOT
    2: /t PORTB = 10101
    3: /t PINB = 111
    Temporary breakpoint 8 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 8, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_SHUTDOWN1

    2: /t PORTB = 11101
    3: /t PINB = 1111
    Temporary breakpoint 9 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 9, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_SHUTDOWN1
    2: /t PORTB = 11101
    3: /t PINB = 1111

    * setting PIN_BOOT
    Temporary breakpoint 10 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 10, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_POWEROFF0
    2: /t PORTB = 11101
    3: /t PINB = 11111
    Temporary breakpoint 11 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 11, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_POWEROFF1
    2: /t PORTB = 10101
    3: /t PINB = 10111
    Temporary breakpoint 12 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 12, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_POWEROFF2
    2: /t PORTB = 10101
    3: /t PINB = 10111

    * entering idle mode
    Temporary breakpoint 13 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 13, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_IDLE0
    2: /t PORTB = 10001
    3: /t PINB = 10011
    Temporary breakpoint 14 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 14, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_IDLE1
    2: /t PORTB = 10001
    3: /t PINB = 10011
    Temporary breakpoint 15 at 0xb0: file ../pipower.c, line 116.

    Temporary breakpoint 15, loop () at ../pipower.c:116
    116	    now = millis();
    1: state = STATE_IDLE2
    2: /t PORTB = 10001
    3: /t PINB = 10011

    * setting quit flag
    main () at ../pipower.c:280
    280	    while (state != STATE_QUIT) {
    1: state = STATE_QUIT
    2: /t PORTB = 10001
    3: /t PINB = 10011
