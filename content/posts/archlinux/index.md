---
categories: [tech]
aliases: ["/2012/12/10/archlinux/"]
title: A first look at Arch Linux
date: "2012-12-10"
---

I decided to take a look at [Arch Linux][] this evening.  It's an
interesting idea, but has a long way to go:

- The installer configured the wrong `root=` command line into my
  `syslinux` configuration, resulting in a system that wouldn't boot.

  **Update**: As far as I can tell, the `syslinux-install_update`
  command doesn't actually make any attempt to configure
  `syslinux.cfg` at all.

- I tried to install `libvirt` and `lxc`, but there are unresolved
  library dependencies...the `virsh` command apparently requires
  `libX11.so.6`, but the package is missing the appropriate
  dependencies to pull in the necessary packages automatically.

- I tried to install `puppet`, but there is no `puppet` package in
  Arch Linux.  One apparently exists in the [Arch User
  Repository][AUR], but there are no packages in Arch Linux that will
  let you install packages from the AUR.

  Arch also seems to be missing `chef`, so there go the two biggest
  names in configuration management.

- There's no way to report bugs without first registering with the bug
  tracking system...and there's no federated login (e.g., with Google,
  Facebook, Twitter, OpenID, etc), so this would be Yet Another
  Account to remember.

So, back to Fedora, I guess.

[Arch Linux]: https://www.archlinux.org/
[AUR]: https://aur.archlinux.org/

