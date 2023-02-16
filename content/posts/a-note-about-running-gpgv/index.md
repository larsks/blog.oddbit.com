---
categories:
- tech
date: '2020-10-05'
filename: 2020-10-05-a-note-about-running-gpgv.md
tags:
- gpg
- encryption
title: A note about running gpgv

---

I found the following error from `gpgv` to be a little opaque:

```
gpgv: unknown type of key resource 'trustedkeys.kbx'
gpgv: keyblock resource '/home/lars/.gnupg/trustedkeys.kbx': General error
gpgv: Can't check signature: No public key
```

It turns out that's gpg-speak for "your `trustedkeys.kbx` keyring doesn't
exist". That took longer to figure out than I care to admit.  To get a key
from your regular public keyring into your trusted keyring, you can run
something like the following:

```
gpg --export -a lars@oddbit.com |
gpg --no-default-keyring --keyring ~/.gnupg/trustedkeys.kbx --import
```

After which `gpgv` works as expected:

```
$ echo hello world | gpg -s -u lars@oddbit.com | gpgv
gpgv: Signature made Mon 05 Oct 2020 07:44:22 PM EDT
gpgv:                using RSA key FDE8364F7FEA3848EF7AD3A6042DF6CF74E4B84C
gpgv:                issuer "lars@oddbit.com"
gpgv: Good signature from "Lars Kellogg-Stedman <lars@oddbit.com>"
gpgv:                 aka "keybase.io/larsks <larsks@keybase.io>"
```
