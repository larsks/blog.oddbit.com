---
categories: [tech]
aliases: ["/2013/11/28/a-python-interface-to-signalfd/"]
title: A Python interface to signalfd() using FFI
date: "2013-11-28"
tags:
  - python
---

I just recently learned about the `signalfd(2)` system call, which was
introduced to the Linux kernel [back in 2007][]:

>  signalfd() creates a file descriptor that can be used to accept
>  signals targeted at the caller.  This provides an alternative to
>  the use  of  a  signal handler  or  sigwaitinfo(2),  and has the
>  advantage that the file descriptor may be monitored by select(2),
>  poll(2), and epoll(7).

The traditional asynchronous delivery mechanism can be tricky to get
right, whereas this provides a convenient fd interface that integrates
nicely with your existing event-based code.

I was interested in using `signalfd()` in some Python code, but Python
does not expose this system call through any of the standard
libraries.  There are a variety of ways one could add support,
including:

- Writing a Python module in C
- Using the `ctypes` module (which I played with [a few years ago][])

[a few years ago]: {{< ref "python-ctypes-module" >}}

However, I decided to use this as an excuse to learn about the
[cffi][] module.  You can find the complete code in my
[python-signalfd][] repository and an explanation of the process
below.

[back in 2007]: http://lwn.net/Articles/225714/
[cffi]: https://pypi.python.org/pypi/cffi
[cffi documentation]: http://cffi.readthedocs.org/

<!-- more -->

The [cffi documentation][] lists a number of principles the project
tries to follow; the first two read as follows:

> - The goal is to call C code from Python. You should be able to do so without learning a 3rd language: every alternative requires you to learn their own language (Cython, SWIG) or API (ctypes)...
> - Keep all the Python-related logic in Python so that you don't need to write much C code (unlike CPython native C extensions).

In practice, what this means is that if the C API documentation for a
function looks like this:

    unsigned int sleep(unsigned int seconds);

Then you can make this function available in Python like this:

    from cffi import FFI
    ffi = FFI()
    crt = ffi.dlopen(None)
    ffi.cdef('unsigned int sleep(unsigned int seconds);')

And to use it:

    crt.sleep(10)

While this works great for a simple function like `sleep`, it gets
slightly more complicated when you function prototype looks like this:

       #include <sys/signalfd.h>
       int signalfd(int fd, const sigset_t *mask, int flags);

If you try what seems obvious given the above example:

    ffi.cdef('''
           #include <sys/signalfd.h>
           int signalfd(int fd, const sigset_t *mask, int flags);
    ''')

You'll run into an error:

    cffi.api.CDefError: cannot parse "#include <sys/signalfd.h>"
    :3: Directives not supported yet

You can try that without the `#include` statement, but you'll just get
a new error:

    cffi.api.CDefError: cannot parse "int signalfd(int fd, const sigset_t *mask, int flags);"
    :3:37: before: *

What all this means is that you need to translate `sigset_t` into
standard C types.  You could go digging through include files in
`/usr/include`, but an easier method is to create a small C source
file like this:

    #include <sys/signalfd.h>

And then run it through the preprocessor:

    $ gcc -E sourcefile.c

Inspecting the output of this command reveals that `sigset_t` is a
typedef for `__sigset_t`, and that `__sigset_t` looks like this:

    typedef struct
      {
        unsigned long int __val[(1024 / (8 * sizeof (unsigned long int)))];
      } __sigset_t;
    typedef __sigset_t sigset_t;

If you plug this into your `cdef`:

    ffi.cdef('''
    typedef struct
    {
      unsigned long int __val[(1024 / (8 * sizeof (unsigned long int)))];
    } __sigset_t;
    typedef __sigset_t sigset_t;

    int signalfd(int fd, const sigset_t *mask, int flags);
    ''')

You end up with the following:

    cffi.api.FFIError: unsupported non-constant or not immediately constant expression

This happens because of the `sizeof()` expression in the `struct`.  We
need to replace that with an actual size.  We can use the
`ffi.sizeof()` method to accomplish the same thing, like this:

    ffi.cdef('''
    typedef struct
    {
      unsigned long int __val[%d];
    } __sigset_t;
    typedef __sigset_t sigset_t;

    int signalfd (int fd, const sigset_t * mask, int flags);
    ''' % ( 1024 / (8 * ffi.sizeof('''unsigned long int''') )))

This will load without error.  You can create a variable suitable for
passing as the `mask` parameter to `signalfd` like this:

    >>> mask = ffi.new('sigset_t *')
    >>> mask
    <cdata 'struct $__sigset_t *' owning 128 bytes>

The trick, of course, is populating that variable correctly.  I ended
up just implementing all of the `sigsetops` functions, which, having
already set up the `sigset_t` structure, meant just adding this:

    ffi.cdef('''
    int sigemptyset(sigset_t *set);
    int sigfillset(sigset_t *set);
    int sigaddset(sigset_t *set, int signum);
    int sigdelset(sigset_t *set, int signum);
    int sigismember(const sigset_t *set, int signum);
    int sigprocmask(int how, const sigset_t *set, sigset_t *oldset);
    ''')

Now we're all set to call these functions through the `crt` variable
we created ealier (by calling `ffi.dlopen(None)`):

    >>> import signal
    >>> mask = ffi.new('sigset_t *')
    >>> crt.sigemptyset(mask)
    0
    >>> crt.sigismember(mask, signal.SIGINT)
    0
    >>> crt.sigaddset(mask, signal.SIGINT)
    0
    >>> crt.sigismember(mask, signal.SIGINT)
    1

And finally, we can all `signalfd()`:

    >>> crt.sigprocmask(0, mask, ffi.NULL)
    0
    >>> fd = crt.signalfd(-1, mask, 0)
    >>> from select import poll
    >>> p = poll()
    >>> p.register(fd)
    >>> p.poll()
    ^C[(3, 1)]
    >>> 

In case it's not obvious from the above example, when I typed
`CONTROL-C` on my keyboard, sending a `SIGINT` to the Python shell, it
caused the `p.poll()` method to exit, reporting activity on fd 3
(which is the fd we were given by `signalfd()`).  We call
`sigprocmask(2)` to prevent the normal asynchronous delivery of
signals, which would otherwise result in Python handling the `SIGINT`
and generating a `KeyboardInterrupt` exception.

You can find this all packaged up nicely with a slightly more pythonic
interface in my [python-signalfd][] repository on GitHub.

---

[Gabe's Geek Log][glog] has an [article about signalfd][] that is also
worth reading.

[python-signalfd]: https://github.com/larsks/python-signalfd
[glog]: http://gabrbedd.wordpress.com/
[article about signalfd]: http://gabrbedd.wordpress.com/2013/07/29/handling-signals-with-signalfd/

