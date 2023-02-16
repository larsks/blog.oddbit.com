---
categories: [tech]
aliases: ["/2014/05/21/sharing-a-terminal-session-wit/"]
title: Sharing a terminal session with termshare
date: "2014-05-21"
tags:
- tools
- terminal
---

[Termshare][] is a tool for sharing your terminal in a browser
session.  It supports both read-only and read-write sessions, and
unlike many other tools it does not require any software installation
on the remote side.  This makes it tremendously handy for:

[termshare]: https://github.com/progrium/termshare

- Streaming terminal demonstrations to a diverse audience, or
- Sharing a terminal session with someone without needing to much
  about with ssh, tmux, screen, etc.

I've successfully used [Termshare][] under both Fedora (19 and 20) and
CentOS.  To get started on these platforms, you'll need to install the
[Go][] language, [git][] for cloning the termshare repository, and
[mercurial][] to support installation of some Go libraries:

    # yum -y install golang git hg

[go]: http://golang.org/
[git]: http://git-scm.org/
[mercurial]: http://mercurial.selenic.com/

Then, clone the [Termshare][] repository:

    $ git clone https://github.com/progrium/termshare.git
    $ cd termshare

Install the Go dependencies:

    $ mkdir gopath
    $ export GOPATH=$PWD/gopath
    $ go get

This will yield...

    go install: no install location for directory /home/lars/src/termshare outside GOPATH

...but you can ignore that.  Then build the software:

    $ make

And you're done!  To start a read-only session, run `./termshare`:

    $ ./termshare
     _                          _                    
    | |_ ___ _ __ _ __ ___  ___| |__   __ _ _ __ ___ 
    | __/ _ \ '__| '_ ` _ \/ __| '_ \ / _` | '__/ _ \
    | ||  __/ |  | | | | | \__ \ | | | (_| | | |  __/
     \__\___|_|  |_| |_| |_|___/_| |_|\__,_|_|  \___|

    Running this open source service supported 100% by community.
    Donate: https://www.gittip.com/termshare

    Session URL: https://termsha.re/12345678-ee85-49ba-66ce-987654321abc

Pass the session URL to people you want to view your terminal.  Run
`./termshare -c` if you want someone to be able to control your
terminal as well as view it.

