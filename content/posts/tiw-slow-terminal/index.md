---
categories:
- tech
date: '2025-10-10'
tags:
- vintage
- serial
title: "Things I Wrote: Slow terminal emulation"
---

Ah, the good old days: when computers were chunky, the Internet was a dream of the future, and you could make a cup of coffee while waiting for a screenful of text to display. If you miss that as much as I do, let me introduce you to [Slow], a low bit rate emulator that lets you travel back in time to those simpler days.

[slow]: https://github.com/larsks/slow

Slow lets you run commands with a reduced output character rate. For example, we can ask for the date at speeds of 50, 75, and 110 bps:

{{< figure src="slow-date.gif" >}}

You're not limited to watching output; you can use Slow to run interactive terminal sessions. Here's `vi` at 300 bps:

{{< figure src="slow-vi.gif" >}}

(We're using `busybox vi` here because many modern text editors spend too much redrawing the screen to be useful at low bitrates.)

