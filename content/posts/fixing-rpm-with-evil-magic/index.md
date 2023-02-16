---
categories: [tech]
aliases: ["/2011/07/26/fixing-rpm-with-evil-magic/"]
title: Fixing RPM with evil magic
date: "2011-07-26"
tags:
  - rpm
  - bad_ideas
---

# Fixing rpmsign with evil magic

At my office we are developing a deployment mechanism for RPM packages. The
general workflow looks like this:

-   You build a source rpm on your own machine.
-   You sign the rpm with your GPG key.
-   You submit the source RPM to our buildserver.
-   The buildserver validates your signature and then builds the package.
-   The buildserver signs the package using a master signing key.

The last step in that sequence represents a problem, because the `rpmsign`
command will always, always prompt for a password and read the response from
`/dev/tty`. This means that (a) you can't easily provide the password on stdin,
and (b) you can't fix the problem using a passwordless key.

Other people have [solved this problem using expect][1], but I've opted for
another solution which in some ways seems cleaner and in others seems like a
terrible idea: function interposition using `LD_PRELOAD`.

The `rpmsign` command prompts for (and reads) a password using the `getpass()`
function call. If you look at the `getpass(3)` man page, you'll see that the
function is defined like this:

    #include <unistd.h>
    char *getpass( const char *prompt); 

So we start with the following short block of C code:

    #include <stdio.h>
    #include <unistd.h>
    
    char *getpass( const char *prompt) {
     printf("I ATE YOUR PASSPHRASE.n");
     return "";
    }
    
This -- when properly loaded -- will replace the standard C library `getpass()` function with our own version, which simply returns an empty string. This of course means we'll be using a passwordless key, but you could obviously have our replacement function return an actual password instead of an empty string. I would argue that by doing so you would not substantially increase the security of your solution.

Next we create a shared library:

    $ cc -fPIC -g   -c -o getpass.o getpass.c
    $ ld -shared -o getpass.so getpass.o
    
And now we perform our magic:

    $ LD_PRELOAD=$(pwd)/getpass.so rpmsign --addsign some.src.rpm
    I ATE YOUR PASSPHRASE.
    Pass phrase is good.

And *voila*! A solution for operating `rpmsign` in batch mode.

[1]: http://jrmonk-techzine.blogspot.com/2010/06/how-to-sign-rpm-files-in-batch-mode.html  

