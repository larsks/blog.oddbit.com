---
categories: [tech]
aliases: ["/2012/07/27/git-fetch-tags-et-al/"]
title: Git fetch, tags, remotes, and more
date: "2012-07-27"
tags:
  - git
---

I’ve been playing around with Git, Puppet, and GPG verification of our
Puppet configuration repository, and these are some random facts about
Git that have come to light as part of the process.

If you want to pull both changes *and* new tags from a remote
repository, you can do this:

    $ git fetch
    $ git fetch --tags

Or you can do this:

    $ git fetch --tags
    $ git fetch

What’s the difference? `git fetch` will leave `FETCH_HEAD` pointing at
the remote `HEAD`, whereas `git fetch --tags` will leave `FETCH_HEAD`
pointing at the most recent tag.

You can also do:

    $ git remote update

Which unlike `git fetch` will pull down any new tags…but unlike
`git fetch --tags` will not update tags that already exist in the local
repository (`git remote update` also sets `FETCH_HEAD` to the remote
`HEAD`).

