---
categories: [tech]
aliases: ["/2019/01/28/losing-malloc/"]
title: "AVR micro-optimization: Losing malloc"
date: "2019-01-28"
tags:
- "avr"
- "attiny85"
- "malloc"
---

Pssst! Hey...hey, buddy, wanna get an extra KB for cheap?

When I write OO-style code in C, I usually start with something like the following, in which I use `malloc()` to allocate memory for a variable of a particular type, perform some initialization actions, and then return it to the caller:

    Button *button_new(uint8_t pin, uint8_t poll_freq) {
        Button *button = (Button *)malloc(sizeof(Button));
        // do some initialization stuff

        return button;
    }

And when initially writing [pipower][], that's exactly what I did.  But while thinking about it after the fact, I realized the following:

[pipower]: {{< ref "pipower-a-raspberry-pi-ups" >}}

- I'm designing for a fixed piece of hardware. I have a fixed number of inputs; I don't actually need to create new `Button` variables dynamically at runtime.
- The ATtiny85 only has 8KB of memory.  Do I really need the overhead of `malloc()`?

The answer, of course, is that no, I don't, so I rewrote the code so that it only has statically allocated structures.  This reduced the size of the resulting binary from this:

    AVR Memory Usage
    ----------------
    Device: attiny85

    Program:    3916 bytes (47.8% Full)
    (.text + .data + .bootloader)

    Data:         35 bytes (6.8% Full)
    (.data + .bss + .noinit)

To this:

    AVR Memory Usage
    ----------------
    Device: attiny85

    Program:    3146 bytes (38.4% Full)
    (.text + .data + .bootloader)

    Data:         29 bytes (5.7% Full)
    (.data + .bss + .noinit)

That's a savings of just under 800 bytes, which on the one hand doesn't seem like it a lot...but on the other hand saves 10% of the available memory!

## Debugging caveat

If you remove `malloc()` from your code and then try to debug it with `gdb`, you may find yourself staring at the following error:

    evaluation of this expression requires the program to have a function "malloc".

This will happen if you ask `gdb` to do something that requires allocating memory for e.g., a string buffer.  The solution is to ensure that `malloc()` is linked into your code when you build for debugging. I use something like the following:

```c
#ifdef DEBUG
__attribute__((optimize("O0")))
void _force_malloc() {
  malloc(0);
}
#endif
```

The `__attribute__((optimize("O0")))` directive disables all optimizations for this function, which should prevent gcc from optimizing out the reference to `malloc()`.
