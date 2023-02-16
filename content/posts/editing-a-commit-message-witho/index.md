---
categories:
- tech
date: '2021-02-18'
draft: false
filename: 2021-02-18-editing-a-commit-message-witho.md
stub: editing-a-commit-message-witho
tags:
- git
title: Editing a commit message without git rebase

---

While working on a pull request I will make liberal use of [git
rebase][] to clean up a series of commits: squashing typos,
re-ordering changes for logical clarity, and so forth. But there are
some times when all I want to do is change a commit message somewhere
down the stack, and I was wondering if I had any options for doing
that without reaching for `git rebase`.

[git rebase]: https://git-scm.com/docs/git-rebase


It turns out the answer is "yes", as long as you have a linear
history.

Let's assume we have a git history that looks like this:

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│ 4be811 │ ◀── │ 519636 │ ◀── │ 38f6fe │ ◀── │ 2951ec │ ◀╴╴ │ master │
└────────┘     └────────┘     └────────┘     └────────┘     └────────┘
```

The corresponding `git log` looks like:

```
commit 2951ec3f54205580979d63614ef2751b61102c5d
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    Add detailed, high quality documentation

commit 38f6fe61ffd444f601ac01ecafcd524487c83394
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    Fixed bug that would erroneously call rm -rf

commit 51963667037ceb79aff8c772a009a5fbe4b8d7d9
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    A very interesting change

commit 4be8115640821df1565c421d8ed848bad34666e5
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    The beginning of time
```

## Mucking about with objects

We would like to modify the message on commit `519636`.

We start by extracting the `commit` object for that commit using `git
cat-file`:

```
$ git cat-file -p 519636
tree 4b825dc642cb6eb9a060e54bf8d69288fbee4904
parent 4be8115640821df1565c421d8ed848bad34666e5
author Alice User <alice@example.com> 978325200 -0500
committer Alice User <alice@example.com> 978325200 -0500

A very interesting change
```

We want to produce a commit object that is identical except for an
updated commit message. That sounds like a job for `sed`! We can strip
the existing message out like this:

```
git cat-file -p 519636 | sed '/^$/q'
```

And we can append a new commit message with the power of `cat`:

```
git cat-file -p 519636 | sed '/^$/q'; cat <<EOF
A very interesting change

Completely refactor the widget implementation to prevent
a tear in the time/space continuum when given invalid
input.
EOF
```

This will give us:

```
tree 4b825dc642cb6eb9a060e54bf8d69288fbee4904
parent 4be8115640821df1565c421d8ed848bad34666e5
author Alice User <alice@example.com> 978325200 -0500
committer Alice User <alice@example.com> 978325200 -0500

A very interesting change

Completely refactor the widget implementation to prevent
a tear in the time/space continuum when given invalid
input.
```

We need to take this modified commit and store it back into the git
object database. We do that using the `git hash-object` command:

```
(git cat-file -p 519636 | sed '/^$/q'; cat <<EOF) | git hash-object -t commit --stdin -w
A very interesting change

Completely refactor the widget implementation to prevent
a tear in the time/space continuum when given invalid
input.
EOF
```

The `-t commit` argument instructs `hash-object` to create a new
commit object. The `--stdin` argument instructs `hash-object` to read
input from `stdin`, while the `-w` argument instructs `hash-object` to
write a new object to the object database, rather than just
calculating the hash and printing it for us.

This will print the hash of the new object on stdout. We can wrap
everything in a `$(...)` expression to capture the output:

```
newref=$(
(git cat-file -p 519636 | sed '/^$/q'; cat <<EOF) | git hash-object -t commit --stdin -w
A very interesting change

Completely refactor the widget implementation to prevent
a tear in the time/space continuum when given invalid
input.
EOF
)
```

At this point we have successfully created a new commit, but it isn't
reachable from anywhere. If we were to run `git log` at this point,
everything would look the same as when we started. We need to walk
back up the tree, starting with the immediate descendant of our target
commit, replacing parent pointers as we go along.

The first thing we need is a list of revisions from our target commit
up to the current `HEAD`. We can get that with `git rev-list`:

```
$ git rev-list 519636..HEAD
2951ec3f54205580979d63614ef2751b61102c5d
38f6fe61ffd444f601ac01ecafcd524487c83394
```

We'll process these in reverse order, so first we modify `38f6fe`:

```
oldref=51963667037ceb79aff8c772a009a5fbe4b8d7d9
newref=$(git cat-file -p 38f6fe61ffd444f601ac01ecafcd524487c83394 |
  sed "s/parent $oldref/parent $newref/" |
  git hash-object -t commit --stdin -w)
```

And then repeat that for the next commit up the tree:

```
oldref=38f6fe61ffd444f601ac01ecafcd524487c83394
newref=$(git cat-file -p 2951ec3f54205580979d63614ef2751b61102c5d |
  sed "s/parent $oldref/parent $newref/" |
  git hash-object -t commit --stdin -w)
```

We've now replaced all the descendants of the modified commit...but
`git log` would *still* show us the old history. The last thing we
need to do is update the branch point to point at the top of the
modified tree. We do that using the `git update-ref` command. Assuming
we're on the `master` branch, the command would look like this:

```
git update-ref refs/heads/master $newref
```

And at this point, running `git log` show us our modified commit in
all its glory:

```
commit 365bc25ee1fe365d5d63d2248b77196d95d9573a
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    Add detailed, high quality documentation

commit 09d6203a2b64c201dde12af7ef5a349e1ae790d7
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    Fixed bug that would erroneously call rm -rf

commit fb01f35c38691eafbf44e9ee86824b594d036ba4
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    A very interesting change

    Completely refactor the widget implementation to prevent
    a tear in the time/space continuum when given invalid
    input.

commit 4be8115640821df1565c421d8ed848bad34666e5
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    The beginning of time
```

Giving us a modified history that looks like:

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│ 4be811 │ ◀── │ fb01f3 │ ◀── │ 09d620 │ ◀── │ 365bc2 │ ◀╴╴ │ master │
└────────┘     └────────┘     └────────┘     └────────┘     └────────┘
```

## Automating the process

Now, that was a lot of manual work. Let's try to automate the process.

```
#!/bin/sh

# get the current branch name
branch=$(git rev-parse --symbolic-full-name HEAD)

# git the full commit id of our target commit (this allows us to
# specify the target as a short commit id, or as something like
# `HEAD~3` or `:/interesting`.
oldref=$(git rev-parse "$1")

# generate a replacement commit object, reading the new commit message
# from stdin.
newref=$(
(git cat-file -p $oldref | sed '/^$/q'; cat) | tee newref.txt | git hash-object -t commit --stdin -w
)

# iterate over commits between our target commit and HEAD in
# reverse order, replacing parent points with updated commit objects
for rev in $(git rev-list --reverse ${oldref}..HEAD); do
  newref=$(git cat-file -p $rev |
    sed "s/parent $oldref/parent $newref/" |
    git hash-object -t commit --stdin -w)
  oldref=$rev
done

# update the branch pointer to the head of the modified tree
git update-ref $branch $newref
```

If we place the above script in `editmsg.sh` and restore our original
revision history, we can run:

```
sh editmsg.sh :/interesting <<EOF
A very interesting change

Completely refactor the widget implementation to prevent
a tear in the time/space continuum when given invalid
input.
EOF
```

And end up with a new history identical to the one we created
manually:

```
commit 365bc25ee1fe365d5d63d2248b77196d95d9573a
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    Add detailed, high quality documentation

commit 09d6203a2b64c201dde12af7ef5a349e1ae790d7
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    Fixed bug that would erroneously call rm -rf

commit fb01f35c38691eafbf44e9ee86824b594d036ba4
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    A very interesting change

    Completely refactor the widget implementation to prevent
    a tear in the time/space continuum when given invalid
    input.

commit 4be8115640821df1565c421d8ed848bad34666e5
Author: Alice User <alice@example.com>
Date:   Mon Jan 1 00:00:00 2001 -0500

    The beginning of time
```

## Caveats

The above script is intentionally simple. If you're interesting in
doing something like this in practice, you should be aware of the
following:

- The above process works great with a linear history, but will break
  things if the rewriting process crosses a merge commit.
- We're assuming that the given target commit is actually reachable
  from the current branch.
- We're assuming that the given target actually exists.

It's possible to check for all of these conditions in our script, but
I'm leaving that as an exercise for the reader.
