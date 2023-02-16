---
categories:
- tech
date: '2020-09-26'
filename: 2020-09-26-vortex-core-keyboard-review.md
tags:
- keyboards
- hardware
title: Vortex Core Keyboard Review
---

I've had my eye on the [Vortex Core][] keyboard for a few months now, and this
past week I finally broke down and bought one (with Cherry MX Brown switches).
The Vortex Core is a 40% keyboard, which means it consists primarily of letter
keys, a few lonely bits of punctuation, and several modifier keys to activate
different layers on the keyboard.

## Physical impressions

It's a really cute keyboard. I'm a big fan of MX brown switches, and this
keyboard is really a joy to type on, at least when you're working primarily
with the alpha keys. I'm still figuring out where some of the punctuation
is, and with a few exceptions I haven't yet spent time trying to remap
things into more convenient positions.

The keyboard feels solid. I'm a little suspicious of the micro-usb
connector; it feels a little wobbly. I wish that it was USB-C and I wish it
felt a little more stable.

Here's a picture of my Core next to my Durgod [K320][]:

{{< figure src="core-vs-k320.jpg" >}}

[k320]: https://www.amazon.com/DURGOD-Mechanical-Interface-Tenkeyless-Anti-Ghosting/dp/B078H3WPHM

## Programming

The keyboard first came out in 2017, and if you read reviews that came out
around that time you'll find several complaints around limitations in the
keyboard's programming features, in particular:

- you can't map the left and right spacebars differently
- you can't remap layer 0
- you can't remap the Fn1 key

And so forth. Fortunately, at some point (maybe 2018) Vortexgear released
updated firmware that resolves all of the above issues, and introduces a
completely new way of programming the keyboard.

Originally, the keyboard was programmed entirely via the keyboard itself: there
was a key combination to activate programming mode in each of the three
programmable layers, and this allowed you to freely remap keys. Unfortunately,
this made it well difficult to share layouts, and made extensive remapping
rather unwieldy.

The [updated firmware][] ("`CORE_MPC`") does away with the hardware
programming, and instead introduces both a web UI for generating keyboard
layouts and a simple mechanism for pushing those layouts to the keyboard that
is completely operating system independent (which is nice if you're a Linux
user and are tired of having to spin up a Windows VM just to run someone's
firmware programming tool). With the new firmware, you hold down `Fn-d` when
booting the keyboard and it will present a FAT-format volume to the operating
system. Drag your layout to the volume, unmount it, and reboot the keyboard and
you're all set (note that you will still need to spin up that Windows VM
one last time in order to install the firmware update).

The Vortexgear keyboard configurator is available at
<http://www.vortexgear.tw/mpc/index.html>, but you're going to want to use
<https://tsfreddie.github.io/much-programming-core/> instead, which removes
several limitations that are present in the official tool.

Because the new configurator (a) allows you to remap all layers, including
layer 0, and (b) allows to create mappings for the `Pn` key, you have a lot
of flexibility in how you set up your mappings.

[updated firmware]: http://www.vortexgear.tw/db/upload/webdata4/6vortex_201861271445393.exe
[vortex core]: http://www.vortexgear.tw/vortex2_2.asp?kind=47&kind2=224&kind3=&kind4=1033

### How I've configured things

I performed some limited remapping of layer 0:

- I've moved the `Fn1` key to the right space bar, and turned the original
  `Fn1` key into the quote key. I use that enough in general writing that
  it's convenient to be able to access it without using a modifier.

- I've set up a cursor cluster using the `Pn` key. This gets me the
  standard `WASD` keys for arrows, and `Q` and `E` for page up and page
  down.

- Holding down the `Pn` key also gets me a numeric keypad on the right side
  of the keyboard.

## Final thoughts

It's a fun keyboard. I'm not sure it's going to become my primary keyboard,
especially for writing code, but I'm definitely happy with it.
