---
categories: [tech]
aliases: ["/2019/01/28/avr-gcc-short-enums/"]
title: "AVR micro-optimization: Avr-gcc and --short-enums"
date: "2019-01-28"
tags:
- "avr"
- "attiny85"
- "avr-gcc"
---

## How big is an enum?

I noticed something odd while browsing through the assembly output of some AVR C code [I wrote recently][pipower]. In the code, I have the following expression:

[pipower]: {{< ref "pipower-a-raspberry-pi-ups" >}}

    int main() {
        setup();

        while (state != STATE_QUIT) {
            loop();
        }
    }

Here, `state` is a variable of type `enum STATE`, which looks something like this (not exactly like this; there are actually [19 possible values][states.h] but I didn't want to clutter this post with unnecessary code listings):

[states.h]: https://github.com/larsks/pipower/blob/master/states.h

    enum STATE {
        STATE_0,
        STATE_1,
        STATE_QUIT
    };

Now, if you do a little research, you'll find that the size of an `enum` is unspecified by the C standard: it is implementation dependent. You will also find [articles](https://www.embedded.fm/blog/2016/6/28/how-big-is-an-enum) that say:

> The GCC C compiler will allocate enough memory for an enum to hold any of the values that you have declared. So, if your code only uses values below 256, your enum should be 8 bits wide.

The boolean expression in the `while` loop gets translated as:

      lds r24,state
      lds r25,state+1
      sbiw r24,2
      brne .L9

In other words, that statement about the GCC compiler doesn't appear to be true: We can see that the compiler is treating the `state` variable as a 16-bit integer despite the `enum` have only three values, which means that (a) two `lds` operations are required to load the value into registers, and (b) it's using `sbiw`, which takes 2 clock cycles, rather than the `cpi` operand, which only takes a single clock cycle.  We see similar behavior in a `switch` statement inside the `loop()` function:

    void loop() {
        switch(state) {
            case STATE_0:
                state = STATE_1;
                break;

            case STATE_1:
                state = STATE_QUIT;
                break;

            case STATE_QUIT:
                break;
        }
    }

The generated assembly for this includes the following:

      lds r24,state
      lds r25,state+1
      cpi r24,1
      cpc r25,__zero_reg__
      breq .L3
      sbiw r24,1
      brsh .L6
      ldi r24,lo8(1)
      ldi r25,0
      sts state+1,r25
      sts state,r24

As before, this requires two `lds` instructions to load a value from the `state` variable:

      lds r24,state
      lds r25,state+1

And two `ldi` + two `sts` instructions to store a new value into the `state` variable:

      ldi r24,lo8(1)
      ldi r25,0
      sts state+1,r25
      sts state,r24

And either multiple instructions (`cpi` + `cpc`) or multi-cycle instructions (`sbiw`) to compare the value in the `state` variable to constant values.

The code we're looking at here isn't at all performance sensitive, but I figured that there had to be a way to get `avr-gcc` to use a smaller data size for this `enum`.  While searching for a solution I stumbled across Rafael Baptista's "[The trouble with GCC's --short-enums flag](https://oroboro.com/short-enum/)", which is an interesting read all by itself but also introduced me to the `--short-enums` flag, which does this:

> Allocate to an "enum" type only as many bytes as it needs for the declared range
> of possible values.  Specifically, the "enum" type is equivalent to the smallest
> integer type that has enough room.

That sure sounds like exactly what I want.  After rebuilding the code using `--short-enums`, the generated assembly for `main()` becomes:

      lds r24,state
      cpi r24,lo8(2)
      brne .L10

The original code required six cycles (`lds` + `lds` + `sbiw`), but this code only takes three (`lds` + `cpi`). The `loop()` function becomes:

      lds r24,state
      mov r24,r24
      ldi r25,0
      cpi r24,1
      cpc r25,__zero_reg__
      breq .L3
      cpi r24,2
      cpc r25,__zero_reg__
      breq .L6
      or r24,r25
      breq .L5
      rjmp .L7
    .L5:
      ldi r24,lo8(1)
      sts state,r24

While the compiler is still performing comparisons on 16 bit values...

      cpi r24,1
      cpc r25,__zero_reg__

...it now only requires a single instruction to load or store values from/to the `state` variable:

      ldi r24,lo8(1)
      sts state,r24

So, the tl;dr is that the `--short-enums` flag makes a lot of sense when compiling code for an 8-bit device, and arguably makes the compiler generate code that is more intuitive.
