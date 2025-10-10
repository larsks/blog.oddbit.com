---
categories:
- tech
date: '2025-10-10'
tags:
- vintage
- serial
- things-i-made
title: "Things I Made: Slow terminal emulation"
---

Ah, the good old days: when computers were chunky, the Internet was a dream of the future, and you could make a cup of coffee while waiting for a screenful of text to display. If you miss that as much as I do, let me introduce you to [Slow], a low bit rate emulator that lets you travel back in time to those simpler days.

[slow]: https://github.com/larsks/slow

Slow lets you run commands with a reduced output character rate. For example, we can ask for the date at speeds of 50, 75, and 110 bps:

{{< figure src="slow-date.gif" >}}

You're not limited to just watching output; you can use Slow to run interactive terminal sessions. Here's `vi` at 300 bps:

{{< figure src="slow-vi-300bps.gif" >}}

And the same thing at 2400 bps:

{{< figure src="slow-vi-2400bps.gif" >}}

(We're using `busybox vi` in these examples because many modern text editors spend too much redrawing the screen to be useful at low bit rates.)

Combine this with something like [Cool Retro Term] for a realistic vintage computing experience!

[cool retro term]: https://github.com/Swordfish90/cool-retro-term
