---
aliases:
- /2017/01/22/making-sure-your-gerrit-changes-aren-t-b/
- /post/2017-01-22-making-sure-your-gerrit-changes-aren-t-b
categories:
- tech
date: '2017-01-22'
tags:
- openstack
- gerrit
- git
title: Making sure your Gerrit changes aren't broken
---

It's a bit of an embarrassment when you submit a review to Gerrit only
to have it fail CI checks immediately because of something as simple
as a syntax error or pep8 failure that you should have caught yourself
before submitting...but you forgot to run your validations before
submitting the change.

In many cases you can alleviate this through the use of the git
`pre-commit` hook, which will run every time you commit changes
locally.  You can have the hook run `tox` or whatever tool your
project uses for validation on every commit.  This works okay for
simple cases, but if the validation takes more than a couple of
seconds the delay can be disruptive to the flow of your work.

What you want is something that stays out of the way while you are
working locally, but that will prevent you from submitting something
for review that's going to fail CI immediately.  If you are using the
[git-review][] tool to interact with Gerrit (and if you're not, you
should be), you're in luck! The `git-review` tool supports a
`pre-review` hook that does exactly what we want.  `git-review` looks
for hooks in a global location (`~/.config/git-review/hooks`) and in a
per-project location (in `.git/hooks/`).  As with standard Git hooks,
the `pre-review` hook must be executable (i.e., `chmod u+x
.git/hooks/pre-review`).

The `pre-review` script will be run before attempting to submit your
changes to Gerrit.  If the script exits successfully, the output is
hidden and your changes will be submitted normally.  If the hook
fails, you will see output along the lines of...

    Custom script execution failed.
    The following command failed with exit code 1
        ".git/hooks/pre-review"
    -----------------------

...followed by the output of the `pre-review` script.

For my work on the [tripleo-quickstart][] project, the contents of my
`.git/hooks/pre-review` script is as simple as:

    #!/bin/sh
    tox

[git-review]: http://docs.openstack.org/infra/git-review/
[tripleo-quickstart]: https://github.com/openstack/tripleo-quickstart