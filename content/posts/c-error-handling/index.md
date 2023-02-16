---
title: Simple error handling in C
date: 2023-02-17
categories: [tech]
tags:
- c
---

## Overview

I was recently working with someone else's C source and I wanted to add some basic error checking without mucking up the code with a bunch of `if` statements and calls to `perror`. I ended up implementing a simple `must` function that checks the return value of an expression, and exits with an error if the return value is less than 0. You use it like this:

```c
must(fd = open("textfile.txt", O_RDONLY));
```

Or:

```c
must(close(fd));
```

In the event that an expression returns an error, the code will exit with a message that shows the file, line, and function in which the error occurred, along with the actual text of the called function and the output of `perror`:

```
example.c:24 in main: fd = open("does-not-exist.xt", O_RDONLY): [2]: No such file or directory
```

To be clear, this is only useful when you're using functions that conform to standard Unix error reporting conventions, and if you're happy with "exit with an error message" as the failure handling mechanism.


## Implementation

The implementation starts with a macro defined in `must.h`:

{{< code language="c" >}}
{{% include file="must.h" %}}
{{< /code >}}

The `__FILE__`, `__LINE__`, and `__func__` symbols are standard predefined symbols provided by `gcc`; they are documented [here](https://gcc.gnu.org/onlinedocs/cpp/Standard-Predefined-Macros.html). The expression `#x` is using the [stringify](https://gcc.gnu.org/onlinedocs/cpp/Stringizing.html#Stringizing) operator to convert the macro argument into a string.

The above macro transforms a call to `must()` into a call to the `_must()` function, which is defined in `must.c`:

{{< code language="c" >}}
{{% include file="must.c" %}}
{{< /code >}}

In this function we check the value of `err` (which will be the return value of the expression passed as the argument to the `must()` macro), and if it evaluates to a number less than 0, we use `snprintf()` to generate a string that we can pass to `perror()`, and finally call `perror()` which will print our information string, a colon, and then the error message corresponding to the value of `errno`.

## Example

You can see `must()` used in practice in the following example program:

{{< code language="c" >}}
{{% include file="example.c" %}}
{{< /code >}}

Provided the `file-that-exists.txt` (a) exists and (b) contains the text `Hello, world.`, and that `file-that-does-not-exist.txt` does not, in fact, exist, running the above code will produce the following output:

```
opening a file that does exist
Hello, world.
opening a file that doesn't exist
example.c:24 in main: fd = open("file-that-does-not-exist.xt", O_RDONLY): [2]: No such file or directory
```
