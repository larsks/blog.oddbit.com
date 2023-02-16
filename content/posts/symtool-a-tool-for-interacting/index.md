---
categories:
- tech
date: '2021-02-06'
filename: 2021-02-06-symtool-a-tool-for-interacting.md
tags:
- python
- '6502'
- retrocomputing
title: 'symtool: a tool for interacting with your SYM-1'

---

The [SYM-1][] is a [6502][]-based single-board computer produced by
[Synertek Systems Corp][synertek] in the mid 1970's. I've had one
floating around in a box for many, many years, and after a recent
foray into the world of 6502 assembly language programming I decided
to pull it out, dust it off, and see if it still works.

[6502]: https://en.wikipedia.org/wiki/MOS_Technology_6502
[sym-1]: https://en.wikipedia.org/wiki/SYM-1
[synertek]: https://en.wikipedia.org/wiki/Synertek

The board I have has a whopping 8KB of memory, and in addition to the
standard SUPERMON monitor it has the expansion ROMs for the Synertek
BASIC interpreter (yet another Microsoft BASIC) and RAE (the "Resident
Assembler Editor"). One interacts with the board either through the
onboard hex keypad and six-digit display, or via a serial connection
at 4800bps (or lower).

[If you're interested in Microsoft BASIC, the [mist64/msbasic][]
repository on GitHub is a trove of information, containing the source
for multiple versions of Microsoft BASIC including the Synertek
version.]

[mist64/msbasic]: https://github.com/mist64/msbasic

Fiddling around with the BASIC interpreter and the onboard assembler
was fun, but I wanted to use a [real editor][vim] for writing source
files, assemble them on my Linux system, and then transfer the
compiled binary to the SYM-1. The first two tasks are easy; there are
lots of editors and there are a variety of 6502 assemblers that will
run under Linux. I'm partial to [ca65][], part of the [cc65][]
project (which is an incredible project that implements a C compiler
that cross-compiles C for 6502 processors). But what's the best way to
get compiled code over to the SYM-1?

[vim]: https://www.vim.org/
[ca65]: https://cc65.github.io/doc/ca65.html
[cc65]: https://cc65.github.io/

## Symtool

That's where [symtool][] comes in. Symtool runs on your host and
talks to the SUPERMON monitor on the SYM-1 over a serial connection.
It allows you to view registers, dump and load memory, fill memory,
and execute code.

[symtool]: https://github.com/larsks/symtool

### Configuration

Symtool needs to know to what serial device your SYM-1 is attached.
You can specify this using the `-d <device>` command line option, but
this quickly gets old. To save typing, you can instead set the
`SYMTOOL_DEVICE` environment variable:

```
$ export SYMTOOL_DEVICE=/dev/ttyUSB0
$ symtool load ...
$ symtool dump ...
```

The baud rate defaults to 4800bps. If for some reason you want to use
a slower speed (maybe you'd like to relive the good old days of 300bps
modems), you can use the `-s` command line option or the
`SYMTOOL_SPEED` environment variable.

### Loading code into memory

After compiling your code (I've included the examples from the SYM-1
Technical Notes [in the repository][code]), use the `load` command to
load the code into the memory of the SYM-1:

[code]: https://github.com/larsks/symtool/tree/master/asm

```
$ make -C asm
[...]
$ symtool -v load 0x200 asm/countdown.bin
INFO:symtool.symtool:using port /dev/ttyUSB0, speed 4800
INFO:symtool.symtool:connecting to sym1...
INFO:symtool.symtool:connected
INFO:symtool.symtool:loading 214 bytes of data at $200
```

(Note the `-v` on the command line there; without that, `symtool`
won't produce any output unless there's an error.)

[A note on compiling code: the build logic in the [`asm/`][code]
directory is configured to load code at address `0x200`. If you want
to load code at a different address, you will need to add the
appropriate `--start-addr` option to `LD65FLAGS` when building, or
modify the linker configuration in `sym1.cfg`.]

### Examining memory

The above command loads the code into memory but doesn't execute it.
We can use the `dump` command to examine memory. By default, `dump`
produces binary output. We can use that to extract code from the SYM-1
ROM or to verify that the code we just loaded was transferred
correctly:

```
$ symtool dump 0x200 $(wc -c < asm/countdown.bin) -o check.bin
$ sha1sum check.bin asm/countdown.bin
5851c40bed8cc8b2a132163234b68a7fc0e434c0  check.bin
5851c40bed8cc8b2a132163234b68a7fc0e434c0  asm/countdown.bin
```

We can also produce a hexdump:

```
$ symtool dump 0x200 $(wc -c < asm/countdown.bin) -h
00000000: 20 86 8B A9 20 85 03 A9  55 8D 7E A6 A9 02 8D 7F   ... ...U.~.....
00000010: A6 A9 40 8D 0B AC A9 4E  8D 06 AC A9 C0 8D 0E AC  ..@....N........
00000020: A9 00 85 02 A9 20 8D 05  AC 18 58 A9 00 8D 40 A6  ..... ....X...@.
00000030: 8D 41 A6 8D 44 A6 8D 45  A6 A5 04 29 0F 20 73 02  .A..D..E...). s.
00000040: 8D 43 A6 A5 04 4A 4A 4A  4A 20 73 02 8D 42 A6 20  .C...JJJJ s..B.
00000050: 06 89 4C 2B 02 48 8A 48  98 48 AD 0D AC 8D 0D AC  ..L+.H.H.H......
00000060: E6 02 A5 02 C9 05 F0 02  50 66 A9 00 85 02 20 78  ........Pf.... x
00000070: 02 50 5D AA BD 29 8C 60  18 A5 04 69 01 18 B8 85  .P]..).`...i....
00000080: 04 C9 FF F0 01 60 A9 7C  8D 41 A6 A9 79 8D 42 A6  .....`.|.A..y.B.
00000090: 8D 43 A6 A9 73 8D 44 A6  A9 00 85 04 20 72 89 20  .C..s.D..... r.
000000A0: 06 89 20 06 89 20 06 89  20 06 89 20 06 89 20 06  .. .. .. .. .. .
000000B0: 89 C6 03 20 06 89 20 06  89 20 06 89 20 06 89 20  ... .. .. .. ..
000000C0: 06 89 20 06 89 A5 03 C9  00 D0 D1 A9 20 85 03 60  .. ......... ..`
000000D0: 68 A8 68 AA 68 40                                 h.h.h@
```

Or a disassembly:

```
$ symtool dump 0x200 $(wc -c < asm/countdown.bin) -d
$0200   20 86 8b    JSR     $8B86
$0203   a9 20       LDA     #$20
$0205   85 03       STA     $03
$0207   a9 55       LDA     #$55
$0209   8d 7e a6    STA     $A67E
$020c   a9 02       LDA     #$02
$020e   8d 7f a6    STA     $A67F
$0211   a9 40       LDA     #$40
$0213   8d 0b ac    STA     $AC0B
$0216   a9 4e       LDA     #$4E
$0218   8d 06 ac    STA     $AC06
$021b   a9 c0       LDA     #$C0
$021d   8d 0e ac    STA     $AC0E
$0220   a9 00       LDA     #$00
$0222   85 02       STA     $02
$0224   a9 20       LDA     #$20
$0226   8d 05 ac    STA     $AC05
$0229   18          CLC
$022a   58          CLI
$022b   a9 00       LDA     #$00
$022d   8d 40 a6    STA     $A640
$0230   8d 41 a6    STA     $A641
$0233   8d 44 a6    STA     $A644
$0236   8d 45 a6    STA     $A645
$0239   a5 04       LDA     $04
$023b   29 0f       AND     #$0F
$023d   20 73 02    JSR     $0273
$0240   8d 43 a6    STA     $A643
$0243   a5 04       LDA     $04
$0245   4a          LSR
$0246   4a          LSR
$0247   4a          LSR
$0248   4a          LSR
$0249   20 73 02    JSR     $0273
$024c   8d 42 a6    STA     $A642
$024f   20 06 89    JSR     $8906
$0252   4c 2b 02    JMP     $022B
$0255   48          PHA
$0256   8a          TXA
$0257   48          PHA
$0258   98          TYA
$0259   48          PHA
$025a   ad 0d ac    LDA     $AC0D
$025d   8d 0d ac    STA     $AC0D
$0260   e6 02       INC     $02
$0262   a5 02       LDA     $02
$0264   c9 05       CMP     #$05
$0266   f0 02       BEQ     $02
$0268   50 66       BVC     $66
$026a   a9 00       LDA     #$00
$026c   85 02       STA     $02
$026e   20 78 02    JSR     $0278
$0271   50 5d       BVC     $5D
$0273   aa          TAX
$0274   bd 29 8c    LDA     $8C29,X
$0277   60          RTS
$0278   18          CLC
$0279   a5 04       LDA     $04
$027b   69 01       ADC     #$01
$027d   18          CLC
$027e   b8          CLV
$027f   85 04       STA     $04
$0281   c9 ff       CMP     #$FF
$0283   f0 01       BEQ     $01
$0285   60          RTS
$0286   a9 7c       LDA     #$7C
$0288   8d 41 a6    STA     $A641
$028b   a9 79       LDA     #$79
$028d   8d 42 a6    STA     $A642
$0290   8d 43 a6    STA     $A643
$0293   a9 73       LDA     #$73
$0295   8d 44 a6    STA     $A644
$0298   a9 00       LDA     #$00
$029a   85 04       STA     $04
$029c   20 72 89    JSR     $8972
$029f   20 06 89    JSR     $8906
$02a2   20 06 89    JSR     $8906
$02a5   20 06 89    JSR     $8906
$02a8   20 06 89    JSR     $8906
$02ab   20 06 89    JSR     $8906
$02ae   20 06 89    JSR     $8906
$02b1   c6 03       DEC     $03
$02b3   20 06 89    JSR     $8906
$02b6   20 06 89    JSR     $8906
$02b9   20 06 89    JSR     $8906
$02bc   20 06 89    JSR     $8906
$02bf   20 06 89    JSR     $8906
$02c2   20 06 89    JSR     $8906
$02c5   a5 03       LDA     $03
$02c7   c9 00       CMP     #$00
$02c9   d0 d1       bNE     $D1
$02cb   a9 20       LDA     #$20
$02cd   85 03       STA     $03
$02cf   60          RTS
$02d0   68          PLA
$02d1   a8          TAY
$02d2   68          PLA
$02d3   aa          TAX
$02d4   68          PLA
$02d5   40          RTI
```

### Executing code

There are two ways to run your code using `symtool`. If you provide
the `-g` option to the `load` command, `symtool` will execute your
code as soon as the load has finished:

```
$ symtool load -g 0x200 asm/countdown.bin
```

Alternatively, you can use the `go` command to run code that has
already been loaded onto the SYM-1:

```
$ symtool go 0x200
```

### Examining registers

The `registers` command allows you to examine the contents of the 6502
registers:

```
$ symtool registers
s ff (11111111)
f b1 (10110001) +carry -zero -intr -dec -oflow +neg
a 80 (10000000)
x 00 (00000000)
y 50 (01010000)
p b0ac (1011000010101100)
```

### Filling memory

If you want to clear a block of memory, you can use the `fill`
command. For example, to wipe out the code we loaded in the earlier
example:

```
$ symtool fill 0x200 0 $(wc -c < asm/countdown.bin)
$ symtool dump -h 0x200 $(wc -c < asm/countdown.bin)
00000000: 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  ................
00000010: 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  ................
[...]
```

### Notes on the code

The `symtool` repository includes both [unit][] and [functional][] tests. The
functional tests require an actual SYM-1 to be attached to your system
(with the device name in the `SYMTOOL_DEVICE` environment variable).
The unit tests will run anywhere.

[unit]: https://github.com/larsks/symtool/tree/master/tests/unit
[functional]: https://github.com/larsks/symtool/tree/master/tests/functional

## Wrapping up

No lie, this is a pretty niche project. I'm not sure how many people
out there own a SYM-1 these days, but this has been fun to work with
and if maybe one other person finds it useful, I would consider that
a success :).

## See Also

- The symtool repository includes an [assembly listing for the
  monitor][supermon].

- [6502.org][] hosts just about [all the SYM-1 documentation].

[supermon]: https://github.com/larsks/symtool/blob/master/reference/synmon11.asm
[6502.org]: http://www.6502.org/
[all the sym-1 documentation]: http://www.6502.org/trainers/synertek/
