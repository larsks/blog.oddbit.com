---
aliases:
- /2017/07/07/better-bulk-filtering-for-gmail/
- /post/2017-07-07-better-bulk-filtering-for-gmail
categories:
- tech
date: '2017-07-07'
tags:
- gmail
title: Better bulk filtering for Gmail
---

I use Gmail extensively for my personal email, and recently my
workplace has been migrated over to Gmail as well.  I find that for my
work email I rely much more extensively on filters and labels to
organize things (like zillions of internal and upstream mailing
lists), and that has posed some challenges.  While Gmail is in general
fairly snappy, attempting to apply an action to thousands of messages
(for example, trying to mark 16000 messages as "read", or applying a
new filter to all your existing messages) results in a very poor
experience: it is not possible to interact with Gmail (in the same
tab) while the action is running, and frequently actions will timeout.

Fortunately, we can take advantage of Gmail's IMAP interface to
overcome most of these obstacles.  The naive approach won't work: If
you attempt to perform an IMAP action against thousands of messages
you will encounter the same timeouts you see with the browser.  The
big advantage to IMAP is that it makes it easy, with a little bit of
code, to split a large operation up into smaller chunks. Gmail
provides a few [IMAP extensions][] that provide us with a mechanism
for accessing Gmail-specific features, such as the rich search syntax
and support for arbitrary labels.

I've written a small tool to take care of this; you can find it in my
[gmailfilters][] repository on GitHub.  The project provides two
commands, the `gmf bulk-filter` command, which I will discuss here,
and the `gmf manage-filters` command, which can translate between a
simpler YAML syntax and the XML syntax used by Gmail's filter
import/export.  I may write about that in a future post.

[gmailfilters]: https://github.com/larsks/gmailfilters

## Installing gmf

The `gmailfilters` project is a standard Python package.  You can
install it directly from GitHub like this:

    pip install git+https://github.com/larsks/gmailfilters

This will install the `gmf` command, which provides the following
subcommands:

- `bulk-filter` -- a command line tool for applying bulk actions to
  Gmail messages.
- `manage-filters` -- translate between a YAML filter syntax and the
  XML syntax used by Gmail for filter import/export.
- `apply-filters` -- read the YAML filters file and apply (a supported
  subset of) the actions to your mail.

This article is going to focus on the `gmf bulk-filter` command.

## Configuring gmf

Once installed, you will need to create a configuration file.  By
default, `gmf` will look for a file named `gmailfilters.yml` located
in your current directory or in your `$XDG_CONFIG_HOME` directory,
typically `$HOME/.config`.  The configuration file looks something
like this:

    accounts:
      default:
        host: imap.gmail.com
        ssl: true
        username: username@example.com
        password: secret-password

You can have multiple accounts in the file; `gmf` will use the one
named `default` by default.

## Using the bulk-filter command

I have a Gmail filter that applies the label `topic/containers` to any
mail matching the search `{docker container kubernetes lxc runc}`.  I
want to apply this filter to all my existing messages, and I want to
mark all matching messages as read so that I can identity new matches.
I can use the `bulk-filter` tool to accomplish this task using the
`--label` and `--flag` options:

    gmf bulk-filter --query '{docker container kubernetes lxc runc}' \
      --label topic/containers --flag seen

It turns out I had close to 15000 freecycle messages gathering dust in
my account.  The messages were already labeled with the `freecycle`
label.  We can weed those out like this:

   gmf bulk-filter --query 'label:freecycle' --trash

The `--trash` option acts like Gmail's "move to trash" option.  You
can also use `--delete`, which will use an IMAP delete operation, but
the behavior of an IMAP delete is controlled by your Gmail
configuration (it may simply archive a message, or it may delete it
completely).

The `bulk-filter` tool can also be used to remove labels by preceding
them with a `-`.  For example, if I want to find all messages labeled
`fedora-devel-list` and modify them so that they are labeled `list`,
`list/fedora`, and `list/fedora/devel` I can run:

    gmf bulk-filter --query 'label:fedora-devel-list' \
      --label list --label list/fedora --label list/fedora-devel
      --label='-fedora-devel-list'

This exposes a quirk of Python's `argparse` argument parser: if the
argument to an option starts with `-`, argparse assumes that you've
made a mistake unless you explicitly attach it to the option with `=`.

By default, the `bulk-filter` tool operates on the `[Gmail]/All mail`
folder, which contains all of your messages.  You can limit it to
specific folders instead by providing an optional list of folders
(that may contain wildcards).  For example, if I want to perform the
above labelling operation only on internal company mailing lists, I
could limit it like this:

    gmf bulk-filter --query '{docker container kubernetes lxc runc}' \
      --label topic/containers list/internal/*

This assumes, of course, that you have filters in place that apply
labels nested under `list/internal` to internal company mailing lists.

The default behavior of `bulk-filter` is to operate on 200 messages at
a time.  You can change this using the `--size` parameter, for
example:

    gmf bulk-filter --size 50 ...