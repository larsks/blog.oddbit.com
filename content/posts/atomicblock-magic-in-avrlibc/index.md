---
categories: [tech]
aliases: ["/2019/02/01/atomicblock-magic-in-avrlibc/"]
title: "ATOMIC_BLOCK magic in avr-libc"
date: "2019-02-01"
tags:
- "avr"
---

The AVR C library, [avr-libc][], provide an `ATOMIC_BLOCK` macro that you can use to wrap critical sections of your code to ensure that interrupts are disabled while the code executes.  At high level, the `ATOMIC_BLOCK` macro (when called using `ATOMIC_FORCEON`) does something like this:

    cli();

    ...your code here...

    seti();

But it's more than that.  If you read [the documentation][] for the macro, it says:

> Creates a block of code that is guaranteed to be executed atomically. Upon entering the block the Global Interrupt Status flag in SREG is disabled, and re-enabled upon exiting the block **from any exit path**.

I didn't really think much about the bit that I've highlighted until I wrote some code that looked something like this:

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
          while(some_condition) {
            if (something_failed)
              goto fail;

            do_something_else();
          }
    }

    fail:
      return false;

There's a `goto` statement there; that's an unconditional jump to the `fail` label outside the `ATOMIC_BLOCK` block. There isn't really any opportunity there for anything to re-enable interrupts, and yet, my code worked just fine. What's going on?

It turns out that this is due to GCC magic.  If you look at the expansion of the `ATOMIC_BLOCK` macro, it looks like this:

    #define ATOMIC_BLOCK(type) for ( type, __ToDo = __iCliRetVal(); \
                               __ToDo ; __ToDo = 0 )

It accepts a `type` parameter which can be one of `ATOMIC_RESTORESTATE` or `ATOMIC_FORCEON`, which look like this:

    #define ATOMIC_RESTORESTATE uint8_t sreg_save \
        __attribute__((__cleanup__(__iRestore))) = SREG

And this:

    #define ATOMIC_FORCEON uint8_t sreg_save \
        __attribute__((__cleanup__(__iSeiParam))) = 0

The magic is the `__attribute__` keyword: GCC supports [custom attributes][] on variables that can change the way the variable is stored or used.  In this case, the code is using the `__cleanup__` attribute, which:

[custom attributes]: https://gcc.gnu.org/onlinedocs/gcc/Common-Variable-Attributes.html

> ...runs a function when the variable goes out of scope.

So when we write:

    ATOMIC_BLOCK(ATOMIC_FORCEON) {
      do_something_here();
    }

That becomes:

    for ( uint8_t sreg_save __attribute__((__cleanup__(__iSeiParam))) = 0, __ToDo = __iCliRetVal(); __ToDo ; __ToDo = 0 ) {
        do_something_here();
    }

Which instructs GCC to ensure that the `iSeiParam` function is run whenever the `sreg_save` variable goes out of scope.  The `iSeiParam()` method looks like:

    static __inline__ void __iSeiParam(const uint8_t *__s)
    {
      __asm__ __volatile__ ("sei" ::: "memory");
      __asm__ volatile ("" ::: "memory");
      (void)__s;
    }

In other words, this is very much like a `try`/`finally` block in Python, although the cleanup action is attached to a particular variable rather than to the block of code itself.  I think that's pretty neat.

[the documentation]: https://www.nongnu.org/avr-libc/user-manual/group__util__atomic.html#gaaaea265b31dabcfb3098bec7685c39e4

[avr-libc]: https://www.nongnu.org/avr-libc/

