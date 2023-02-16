---
categories: [tech]
date: '2019-06-14'
filename: 2019-06-14-git-etiquette-commit-messages.md
tags:
- git
- github
title: 'Git Etiquette: Commit messages and pull requests'

---

## Always work on a branch (never commit on master)

When working with an upstream codebase, always make your changes on a feature branch rather than your local `master` branch. This will make it easier to keep your local `master` branch current with respect to upstream, and can help avoid situations in which you accidentally overwrite your local changes or introduce unnecessary merge commits into your history.

## Rebase instead of merge

If you need to incorporate changes from the upstream `master` branch in the feature branch on which you are currently doing, bring in those changes using `git rebase` rather than `git merge`.  This process will generally start by ensuring that your local copy of the upstream `master` is current:

```
git remote update

```

Followed by rebasing your changes on top of that branch:

```
git rebase origin/master
```

## Make your commit messages meaningful

Your commit messages should follow common best practices, such as [those documented for OpenStack][].  In general, this means:

- Your commit message should have the subject on the first line, then a blank line, then the message body.

- The message body should be wrapped at around 75 characters.

- Your commit message should succinctly describe *what* was changed and *why* it was changed.

- If your commit is associated with a bug, user story, task, or other tracking mechanism, include a reference to the appropriate item in your commit message.

### Example of bad commit messages

1. This should probably have been squashed with the commit that introduced the typo:

    ```
    Fixed a typo.
    ```

2. This doesn't provide sufficient details:

    ```
    Trying that thing again
    ```

3. Changes necessary to resolve merge conflicts should generally be squashed into the commits that introduce the conflict:

    ```
    Fixing merge conflicts
    ```

### Example of good commit messages

1. A constructed example:

    ```
    Support new "description" field on all widgets (TG-100)

    Update both the database model and the web UI to support an extended
    "description" field on all objects. This allows us to generate more useful
    product listings.
    ```

2.  from https://github.com/openstack/ironic/commit/6ca99d67302d7e1b639ad9b745631e65a4b2f25c:

    ```
    Add release note updating status of smartnics

    Smartnic support merged into Neutron a few weeks ago,
    and as we downplayed the functionality during the Stein
    cycle, we should highlight it during Train since it should
    now be available.

    Change-Id: I19372a0ede703f62940bbb2cc3a80618560ebc93
    ```


3.  from https://github.com/ansible/ansible/commit/88a1fc28d894575d48edc3817cc1a8ef4dca3cae:

    ```
    Clean up iosxr get_config_diff function (#57589)

    This fixes an index error issue when running tests on zuul.ansible.com
    for iosxr. We can fix this by getting the last element in the list.
    ```

[those documented for openstack]: https://wiki.openstack.org/wiki/GitCommitMessages

## Fix typos by amending or rebasing

If before your pull request has merged you realize you need to fix a typo or other error, do not create a new commit with the correction.  

If the typo is in the most recent commit, simply fix it, `git add` the change, and then use `git commit --amend` to update the latest commit.

If the typo is **not** in the latest commit, then use `git rebase` to edit the commit. The procedure will look something like this:

1. Assuming that your branch is based on `origin/master`, run `git rebase -i origin/master`. This will bring up the "pick list", which allows you to select among various actions for each commit between `origin/master` and your current branch. For example:

    ```
    pick 6ca99d673 Add release note updating status of smartnics
    pick c2ab34a8c Do not log an exception if Allocation is deleted during handling.
    pick 87464fbbc Change constraints opendev.org to release.openstack.org
    pick 43f7bf9f0 Fix :param: in docstring
    ```

2. Change `pick` to `edit` for the commit you wish to edit, then exit your editor.

3. Make the necessary change, then `git add` your modified files and then `git rebase --continue`.

In either of the above situations, when you have committed the changes locally, run `git push -f` to update the remote branch on GitHub (which will in turn update your pull request).

## Have one commit per logical change and one major feature per pull request

When you submit a pull request, all the commits associated with that pull request should be related to the same major feature. For example, if you made the follow changes:

- Fixed bug #1234
- Wrote new feature discussed at last planning session

Those should be two separate pull requests.  On the other hand, if you have instead made these changes:

- Wrote new feature discussed at last planning session
- Wrote documentation for new feature
- Wrote tests for new feature

Those could all be made part of the same pull request.

Within your pull request, there should be a single commit for each logical change.  For example rather than:

- Started documentation for new feature
- Made changes to documentation based on review
- Reformatted documentation to fix syntax error

You should have a single commit:

- Write documentation for new feature

You should use `git commit --amend` or `git rebase`, as discussed earlier, to keep your commits topical and organized.
