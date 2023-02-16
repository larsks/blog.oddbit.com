---
categories:
- tech
date: '2019-10-03'
filename: 2019-10-03-tm-v71a-linux-part-1.md
tags:
- hamradio
- linux
title: 'TM-V71A and Linux, part 1: Programming mode'
---

I recently acquired my Technician amateur radio license, and like many folks my first radio purchase was a [Baofeng UV-5R][]. Due to its low cost, this is a very popular radio, and there is excellent open source software available for programming it in the form of the [CHIRP][] project. After futzing around with the UV-5R for a while, I wanted to get something a little nicer for use at home, so I purchased a [Kenwood TM-V71A][]. CHIRP claims to have support for this radio as well, but it turns out it's not very good: it uses a "live" connection so every time you edit a channel it tries to update the radio. This result in a slow and flaky UI, especially when trying to make bulk changes (like relocating a block of channels). I ended up using Kenwood's official [MCP-2A][] software running on a Windows guest on my system, which works but isn't ideal. I decided to learn more about how the radio interacts with the computer to see if I could improve the situation.

[baofeng uv-5r]: https://baofengtech.com/uv-5r?PageSpeed=noscript
[kenwood tm-v71a]: https://www.kenwood.com/usa/com/amateur/tm-v71a/
[chirp]: https://chirp.danplanet.com/projects/chirp/wiki/Home

---

## Existing solutions

The [Hamlib][] project has an [existing TM-D710 driver][] that also support the TM-V71. Using either the `rigctl` command line tool or using the Hamlib API, it is possible to...

- Control PTT on the radio
- Tune to a specific frequency
- Tune to a specific memory channel
- Change the current modulation (AM/FM/NFM)

...and perform a few other actions. However, neither the command line tool nor the API appear to provide facilities for importing/exporting channels, editing channels, performing a memory backup and restore, and so forth.  Additionaly, I do most of development these days in Python. While there exists a Python binding for Hamlib, it's not terrible intuitive.

## Programming mode

The way the MCP-2A program interacts with the TM-V71 is via a memory dump and restore process (which is much like how CHIRP interacts with Baofeng radios). This makes use of the radio's "programming mode", and support for that in Hamlib doesn't exist.  In fact, while the control commands for the radio have been documented in various places (such as LA3QMA's [TM-V71_TM-D710-Kenwood repository][]), I was not able to find any documentation that described how to interact with the radio in programming mode.  In order to figure out how things work, I would need to trace the interaction between MCP-2A and the radio.

I run MCP-2A in a Windows 10 guest on my Linux host. Normally, when configuring the radio, I expose the USB serial adapter to the Windows guest using the USB redirection feature offered by libvirt.  In order to trace the interaction between the software and the radio, I need to stick something in between that will log the data being sent back and forth.

I started by configuring a serial port on the Windows guest that was connected to a Unix socket:

```xml
<serial type='unix'>
  <source mode='bind' path='/tmp/win10-serial'/>
  <target type='isa-serial' port='1'>
    <model name='isa-serial'/>
  </target>
</serial>
```

This exposes a Unix socket at `/tmp/win10-serial` when the guest is running. On the host, I use [socat][] as a proxy between that socket and the actual serial port. I ended up running `socat` like this:

```
socat -x -v \
        /dev/ttyUSB1,b57600,crtscts=1,raw,echo=0 \
        unix-connect:/tmp/win10-serial
```

The `-x` and `-v` options instruct `socat` to log on stdout data passing through the proxy, in both raw and hexadecimal format. With the proxy running, I started MCP-2A on the Windows guest and performed a "Read data from the transceiver" operation.  This resulted in a log that looks like the following:

```
< 2019/09/28 14:42:32.732010  length=1 from=0 to=0
 49                                               I
--
< 2019/09/28 14:42:32.834799  length=1 from=1 to=1
 44                                               D
--
< 2019/09/28 14:42:33.043626  length=1 from=2 to=2
 0d                                               .
--
> 2019/09/28 14:42:33.069589  length=10 from=0 to=9
 49 44 20 54 4d 2d 56 37 31 0d                    ID TM-V71.
[...]
```

In this output, chunks marked with `<` represent data sent FROM the software TO the radio, and chunks marked with `>` represent data sent FROM the radio TO the software.  The information we need is there, but the output is a little too cluttered, making it hard to interpret. I wrote a quick script to clean it up; after processing, the beginning of the transaction look like this (where `<<<` represents date being sent to the radio, and `>>>` represents data received from the radio):

```
<<< 00000000: 49                                                I
<<< 00000000: 44                                                D
<<< 00000000: 0D                                                .
>>> 00000000: 49 44 20 54 4D 2D 56 37  31 0D                    ID TM-V71.
<<< 00000000: 54 43 20 31 0D                                    TC 1.
>>> 00000000: 3F 0D                                             ?.
<<< 00000000: 49 44 0D                                          ID.
>>> 00000000: 49 44 20 54 4D 2D 56 37  31 0D                    ID TM-V71.
<<< 00000000: 54 59 0D                                          TY.
>>> 00000000: 54 59 20 4B 2C 30 2C 30  2C 31 2C 30 0D           TY K,0,0,1,0.
<<< 00000000: 46 56 20 30                                       FV 0
<<< 00000000: 0D                                                .
>>> 00000000: 46 56 20 30 2C 31 2E 30  30 2C 32 2E 31 30 2C 41  FV 0,1.00,2.10,A
>>> 00000000: 2C 31 0D                                          ,1.
<<< 00000000: 30 4D 20 50                                       0M P
<<< 00000000: 52 4F 47 52 41 4D 0D                              ROGRAM.
>>> 00000000: 30 4D 0D                                          0M.
<<< 00000000: 52 00                                             R.
<<< 00000000: 00 00                                             ..
>>> 00000000: 57 00 00 00 00 4B 01 FF  FF FF FF FF FF FF FF FF  W....K..........
>>> 00000000: FF 00 FF FF 00 00 39 31  35 01 00 00 00 00 01 01  ......915.......
>>> 00000000: 00 00 00 01 02 03 00 00  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF                                       ....
<<< 00000000: 06                                                .
>>> 00000000: 06                                                .
<<< 00000000: 52 01                                             R.
<<< 00000000: 00 00                                             ..
>>> 00000000: 57 01 00 00 FF FF FF FF  FF FF FF FF FF FF FF FF  W...............
[...]
```

And the end of the transaction looks like this:

```
[...]
<<< 00000000: 52 7E 00                                          R~.
<<< 00000000: 00                                                .
>>> 00000000: 57 7E 00 00 FF FF FF FF  FF FF FF FF FF FF FF FF  W~..............
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
>>> 00000000: FF FF FF FF                                       ....
<<< 00000000: 06                                                .
>>> 00000000: 06                                                .
<<< 00000000: 45                                                E
>>> 00000000: 06 0D                                             ..
>>> 00000000: 00                                                .
```

This is a lot easier to read. We can see the software initially sends some commands to identify the radio:

- `ID` to get the radio model
- `TY` to get the radio type
- `FV 0` to get the firmware version

And then enters programming mode by sending `0M PROGRAM`. Inspecting the remainder of the dump  shows us that the software makes a series of read requests that look like:

```
<<< 00000000: 52 00                                             R.
<<< 00000000: 00 00                                             ..
```

That is, a four byte request of the form:

1. `R`
1. Address (2 bytes)
1. Size

When a read request has a size of `0`, that means `read 256 bytes`.

The response to a read request looks like:

```
>>> 00000000: 57 00 00 00 00 4B 01 FF  FF FF FF FF FF FF FF FF  W....K..........
>>> 00000000: FF 00 FF FF 00 00 39 31  35 01 00 00 00 00 01 01  ......915.......
>>> ...
```

That is:

1. `W`
1. Address (2 bytes)
1. Size
1. `<Size>` bytes of data

It turns out that the response to the read request is exactly the syntax used to perform a write request. The log of the write operation starts like this:

```
<<< 00000000: 54 43 20                                          TC 
<<< 00000000: 31 0D                                             1.
>>> 00000000: 3F 0D                                             ?.
<<< 00000000: 49                                                I
<<< 00000000: 44 0D                                             D.
>>> 00000000: 49 44 20 54 4D 2D 56 37  31 0D                    ID TM-V71.
<<< 00000000: 54 59 0D                                          TY.
>>> 00000000: 54 59 20 4B 2C 30 2C 30  2C 31 2C 30 0D           TY K,0,0,1,0.
<<< 00000000: 46 56                                             FV
<<< 00000000: 20 30 0D                                           0.
>>> 00000000: 46 56 20 30 2C 31 2E 30  30 2C 32 2E 31 30 2C 41  FV 0,1.00,2.10,A
>>> 00000000: 2C 31 0D                                          ,1.
<<< 00000000: 30 4D                                             0M
<<< 00000000: 20 50 52 4F 47 52 41 4D  0D                        PROGRAM.
>>> 00000000: 30 4D 0D                                          0M.
<<< 00000000: 52                                                R
<<< 00000000: 00 00 04                                          ...
>>> 00000000: 57 00 00 04 00 4B 01 FF                           W....K..
<<< 00000000: 06                                                .
>>> 00000000: 06                                                .
<<< 00000000: 57 00                                             W.
<<< 00000000: 00 01 FF                                          ...
>>> 00000000: 06                                                .
<<< 00000000: 57 00                                             W.
<<< 00000000: 04 FC FF FF FF FF FF FF  FF FF FF 00              ............
<<< 00000000: FF FF 00 00 39 31 35 01  00 00 00 00              ....915.....
<<< 00000000: 01 01 00 00 00 01 02                              .......
<<< 00000000: 03 00 00 FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000010: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000020: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000030: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000040: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000050: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000060: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000070: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000080: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000000: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000010: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000020: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000030: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF FF  ................
<<< 00000040: FF FF FF FF FF FF FF FF  FF FF FF FF FF FF FF     ...............
>>> 00000000: 06                                                .
[...]
```

And concludes with:

```
[...]
<<< 00000000: 57 00                                             W.
<<< 00000000: 00 04 00 4B 01 FF                                 ...K..
>>> 00000000: 06                                                .
<<< 00000000: 45                                                E
>>> 00000000: 06 0D                                             ..
>>> 00000000: 00                                                .
```

In this log, we see a series of write requests; for example:

```
<<< 00000000: 57 00                                             W.
<<< 00000000: 00 01 FF                                          ...
>>> 00000000: 06                                                .
```

In the above trace, the software is first writing one byte (`0xFF`) to address `0x0`. The radio acknowledges a write request with a response byte (`0x06`).

By experimenting a bit, it seems as if writing `0xFF` to `0x0`, will cause the radio to reset to defaults when you exit programming mode. That's why at the conclusion of the write operation, we see the following:

```
<<< 00000000: 57 00                                             W.
<<< 00000000: 00 04 00 4B 01 FF                                 ...K..
>>> 00000000: 06                                                .
```

That is, the software is rewriting the first four bytes of memory with their original contents.

### A warning about manual interaction

If you manually place the radio into programming mode, you will see that after entering `0M PROGRAM` the radio displays `PROG MCP`. Unless you are a preternaturally fast typist, the radio display will shortly switch to `PROG ERR` because of the delay between entering programming mode and any read or write transactions. In this state, you will still be able to enter read or write commands, but the status byte in response to a successful write command will be `0x15` instead of `0x06`.

---

I've summarized this information in a document that I submitted as a pull request to <https://github.com/LA3QMA/TM-V71_TM-D710-Kenwood/>. You can read it [here][].

[here]: https://github.com/LA3QMA/TM-V71_TM-D710-Kenwood/blob/master/PROGRAMMING_MODE.md


[TM-V71_TM-D710-Kenwood repository]: https://github.com/LA3QMA/TM-V71_TM-D710-Kenwood/blob/master/commands/MR.md
[hamlib]: https://hamlib.github.io/
[existing TM-D710 driver]: https://github.com/Hamlib/Hamlib/blob/master/kenwood/tmd710.c
[socat]: http://www.dest-unreach.org/socat/
[MCP-2A]: https://www.kenwood.com/i/products/info/amateur/mcp_2a.html