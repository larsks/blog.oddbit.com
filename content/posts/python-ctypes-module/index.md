---
categories: [tech]
aliases: ["/2010/08/10/python-ctypes-module/"]
title: Python ctypes module
date: "2010-08-10"
tags:
  - python
---

I just learned about the Python `ctypes` module, which is a Python module for interfacing with C code. Among other things, `ctypes` lets you call arbitrary functions in shared libraries. This is, from my perspective, some very cool magic. I thought I would provide a short example here, since it took me a little time to get everything working smoothly.

For this example, we'll write a wrapper for the standard `statvfs(2)` function:
    
    
    SYNOPSIS
           #include <sys/statvfs.h>
    
           int statvfs(const char *path, struct statvfs *buf);
           int fstatvfs(int fd, struct statvfs *buf);
    
    DESCRIPTION
           The function statvfs() returns information about a mounted file
           system.  path is the pathname of any file within the mounted file
           system.   buf is a pointer to a statvfs structure defined
           approximately as follows:
    

Note the wording there: "...defined _approximately_ as follows." Our first job is finding out exactly what the `statvfs` structure looks like. We can use gcc to show us the contents of the appropriate #include file:
    
    
    echo '#include <sys/statvfs.h>' | gcc -E | less
    

Browsing through the results, we find the the following definition:
    
    
    struct statvfs
      {
        unsigned long int f_bsize;
        unsigned long int f_frsize;
    
        __fsblkcnt_t f_blocks;
        __fsblkcnt_t f_bfree;
        __fsblkcnt_t f_bavail;
        __fsfilcnt_t f_files;
        __fsfilcnt_t f_ffree;
        __fsfilcnt_t f_favail;
        unsigned long int f_fsid;
    
        unsigned long int f_flag;
        unsigned long int f_namemax;
        int __f_spare[6];
      };
    

We need to investigate further to determine what `__fsblkcnt_t` and `__fsfilcnt_t` really mean. There are a number of ways to do this. Here's what I did:

    $ cd /usr/include
    $ ctags -R
    $ ex
    Entering Ex mode.  Type "visual" to go to Normal mode.
    :tag __fsblkcnt_t
    "bits/types.h" [readonly] 197L, 7601C
    :p
    __STD_TYPE __FSBLKCNT_T_TYPE __fsblkcnt_t;
    :tag __FSBLKCNT_T_TYPE
    "bits/typesizes.h" [readonly] 66L, 2538C
    :p
    #define __FSBLKCNT_T_TYPE       __ULONGWORD_TYPE
    :tag __ULONGWORD_TYPE
    "bits/types.h" [readonly] 197L, 7601C
    :p
    #define __ULONGWORD_TYPE        unsigned long int

Repeat this for `__fsfilcnt_t` and we find that they are both unsigned long int.

This means that we need to create a `ctypes.Structure` object like the following:

    from ctypes import *
    
    class struct_statvfs (Structure):
        _fields_ = [
                ('f_bsize', c_ulong),
                ('f_frsize', c_ulong),
                ('f_blocks', c_ulong),
                ('f_bfree', c_ulong),
                ('f_bavail', c_ulong),
                ('f_files', c_ulong),
                ('f_ffree', c_ulong),
                ('f_favail', c_ulong),
                ('f_fsid', c_ulong),
                ('f_flag', c_ulong),
                ('f_namemax', c_ulong),
                ('__f_spare', c_int * 6),
                ]
    
Failure to create the correct structure (e.g., if you're missing fields) can result in a number of weird errors, including segfaults and warnings from gcc about memory corruption.

Now that we have the appropriate structure defined, we need to load up the appropriate shared library:

    libc = CDLL('libc.so.6')

And then tell ctypes about the function arguments expected by statvfs():

    libc.statvfs.argtypes = [c_char_p, POINTER(struct_statvfs)]

With all this in place, we can now call the function:
    
    s = struct_statvfs()
    res = libc.statvfs('/etc', byref(s))
    for k in s._fields_:
        print '%20s: %s' % (k[0], getattr(s, k[0]))

We use `byref(s)` because `statvfs()` expects a pointer to a structure. This outputs the following on my local system:
    
     f_bsize: 4096
    f_frsize: 4096
    f_blocks: 10079070
     f_bfree: 5043632
    f_bavail: 4941270
     f_files: 2564096
     f_ffree: 2419876
    f_favail: 2419876
      f_fsid: 18446744071962486827
      f_flag: 4096
    f_namemax: 255
    __f_spare: <__main__.c_int_Array_6 object at 0x7f718fb6b3b0>

