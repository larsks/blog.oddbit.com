---
categories: [tech]
aliases: ["/2013/01/25/archlinux-second-look/"]
title: A second look at Arch Linux
date: "2013-01-25"
---

This is a followup to an [earlier post about Arch Linux][previous].

I've since spent a little more time working with Arch, and these are
the things I like:

- The base system is very small and has a very short boot time.  I
  replaced Ubuntu on my old [Eee PC][] with Arch and suddenly the boot
  time is reasonable (< 10 seconds to a text prompt, < 30 seconds to a
  full GUI login).

- I feel better about the Arch installation process after seeing what
  happened to Anaconda (the Fedora installer) in Fedora 18.

- I have been pleasantly surprised at the speed with which bug reports
  have been addressed.

- I really like the fact that Arch has completely converted over to
  [systemd][].  There are no legacy init scripts, the base system
  relies on the systemd journal for logging, etc.

[systemd]: http://www.freedesktop.org/wiki/Software/systemd

I run a KVM-based virtualization environment at home, and I've
switched to Arch on the physical host because of its small footprint
(and because it tends to have very recent versions of the various
libvirt-related tools).

Things that still bother me:

- The [Arch User Repository][aur] is a train wreck.  The fact that
  there are no tools in the standard repositories for working with the
  AUR is a good sign that nobody really trusts it, and despite
  language to the contrary there does not appear to be much movement
  from the AUR in to the Community repository.

- Packages in general are not curated with same care as in Fedora.  It
  is much more common in Arch to find packages that either have broken
  dependencies (e.g., they require a shared library that is not
  actually installed) or they have unreasonably broad dependencies
  (which can happen if a package includes both GUI and command line
  tools, rather than splitting them into separate package).  In
  particular, my experience here highlights the value of (a) the
  automatic dependency mechanisms invoked by `rpmbuild` (finding
  shared libraries, Python/Perl/Ruby modules required by scripts, etc)
  and (b) the use of a tool such as `mock` for building packages in a
  "pristine" environment.

- The average age on [#archlinux][irc] appears to be 13.  I'm not sure
  what's up with that (does anyone maintain age demographics for Linux
  distributions?). Do we really need "b00bs" in the `/topic`?

Also, and this is completely unrelated to anything else, I am terribly
disappointed that the Arch forums are hosted at
<http://bbs.archlinux.org> but there is no actual BBS
([e.g.][synchronet]) running on
port 23.  Because that would be cool.

[previous]: /post/a-first-look-at-arch-linux
[eee pc]: https://en.wikipedia.org/wiki/Asus_Eee_PC#Eee_900_series
[aur]: https://aur.archlinux.org/
[synchronet]: http://www.synchro.net/
[irc]: https://wiki.archlinux.org/index.php/IRC_Channel

