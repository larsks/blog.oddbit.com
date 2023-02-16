---
categories: [tech]
aliases: ["/2016/02/19/a-collection-of-git-tips/"]
title: "A collection of git tips"
date: "2016-02-19"
tags:
  - git
---

This is a small collection of simple `git` tips and tricks I use to
make my life easier.

## Quickly amend an existing commit with new files

I have this alias in place that will amend the current commit while
automatically re-using the existing commit message:

    alias.fix=commit --amend -C HEAD

With this in place, fixing a review becomes:

    $ vim some/file/somewhere
    $ git add -u
    $ git fix

Which I find much more convenient than `git commit --amend`, following
by saving the commit message.

## What files have changed?

Sometimes, I just want to know what files were changed in a commit.  I
have the following alias, because I have a hard time remembering
whether I want `--name-only` or `--names-only` or `--only-names`...

    alias.changed=show --name-only

Which gets me the commit message and a list of changed files:

    $ git changed
    commit 8c2a00809817a047bf312b72f390b5cb50ef9819
    Author: Lars Kellogg-Stedman <lars@redhat.com>
    Date:   Wed Feb 17 11:11:02 2016 -0500

        yet another attempt at fixing image fetching
        
        this uses curl rather than wget, because wget chokes on file:// urls
        which makes it difficult to cache images locally.  curl supports
        resuming downloads, but explicitly rather than implicitly like wget,
        so we need a do/until loop.
        
        Change-Id: Ibd3c524ea6ddfd423aec439f9eb7fffa62dfe818

    :100644 100644 342a002... 2b9f9cb... M  playbooks/roles/libvirt/setup/undercloud/tasks/main.yml
    :100644 000000 d22cb99... 0000000... D  playbooks/roles/libvirt/setup/undercloud/templates/get-undercloud.sh.j2

## Getting the name of the current branch

For scripting purposes I often want the name of the current branch.
Rather than reading `git rev-parse --help` every time, I have this
alias:

    alias.branch-name=rev-parse --abbrev-ref --symbolic-full-name HEAD

Which gets me:

    $ git branch-name
    master
    $ git checkout bug/missing-become
    $ git branch-name
    bug/missing-become

## Prevent accidental commits on master

When working on upstream projects I always want to be working on a
feature branch.  To prevent accidental commits on master I drop the
following script into `.git/hooks/pre-commit`:

    #!/bin/sh

    current_branch=$(git branch-name)

    if [ "$current_branch" = "master" ]; then
      echo "*** DO NOT COMMIT ON MASTER"
      exit 1
    fi

    exit 0

If I try to commit to my local `master` branch, I get:

    $ git ci -m 'made a nifty change'
    *** DO NOT COMMIT ON MASTER

