---
categories: [tech]
aliases: ["/2015/10/19/automatic-git-cache/"]
title: "Automatic git cache"
date: "2015-10-19"
tags:
  - git
---

This post is in response to a comment someone made on irc earlier
today:

> [I] would really like a git lookaside cache which operated on an upstream
> repo, but pulled objects locally when they're available

In this post I present a proof-of-concept solution to this request.
Please note that thisand isn't something that has actually been used
or tested anywhere!

If you access a git repository via `ssh`, it's easy to provide a
wrapper for git operations via the `command=` option in an
`authorized_keys` file.  We can take advantage of this to update a a
local "cache" repository prior to responding to a `clone`/`pull`/etc.
operation.

A simple wrapper might look like this:

    #!/bin/bash

    [ "$SSH_ORIGINAL_COMMAND" ] || exit 1

    eval set -- $SSH_ORIGINAL_COMMAND

    cd repos

    case $1 in
      (git-receive-pack|git-upload-pack)
        :;;
      (*)	echo "*** Unrecognized command." >&2
        exit 1
        ;;
    esac

    if [ "$1" = "git-upload-pack" ]; then
      (
      # Update the local repository cache if the file 
      # 'git-auto-update' exists.
      cd "$2"
      [ -f git-auto-update ] &&
        git remote update >&2
      )
    fi

    exec "$@"

If we have a `git` user locally, we can place the above script into
`/home/git/bin/gitwrapper`, and then set up a `.ssh/authorized_keys`
file that looks something like this:

    command="/home/git/bin/gitwrapper" ssh-rsa AAAAB3NzaC...

Let's set up a local repository mirror:

    # su - git
    git$ mkdir repos
    git$ cd repos
    git$ git clone --mirror http://github.com/openstack-dev/devstack.git

In order to tell the wrapper script that it should perform the
automatic update logic on this repository, we need to touch the
appropriate flag file:

    git$ touch devstack.git/git-auto-update

If we then attempt to clone that repository:

    lars$ git clone git@localhost:devstack.git

The wrapper script will check for the presence of that flag file, and
if it exists it will first perform a `git remote update` before
responding to the `clone` operation.  This ensures that any new
objects are fetched, while ensuring fast transfer of objects that are
already available locally.  The output we see after running the above
`git clone` looks something like:

    Fetching origin
    From http://github.com/openstack-dev/devstack
       8ce00ac..0ba1848  master     -> master
    First, rewinding head to replay your work on top of it...
    Fast-forwarded master to 0ba18481672964808bbbc4160643387dc931c654.

The first three lines are the result `git remote update` operation in
our cache repository.

