---
categories: [tech]
date: '2019-06-17'
filename: 2019-06-17-avoid-rebase-hell-squashing-wi.md
tags:
- git
title: 'Avoid rebase hell: squashing without rebasing'

---

You're working on a pull request. You've been working on a pull request for a while, and due to lack of sleep or inebriation you've been merging changes into your feature branch rather than rebasing. You now have a pull request that looks like this (I've marked merge commits with the text `[merge]`):

```
7e181479 Adds methods for widget sales
0487162 [merge] Merge remote-tracking branch 'origin/master' into my_feature
76ee81c [merge] Merge branch 'my_feature' of https://github.com/my_user_name/widgets into my_feature
981aab4 Adds api for the widget service.
b048836 Includes fixes suggested by reviewer.
3dd0c22 adds changes requested by reviewer
5891db2 [merge] fixing merge conflicts
2e226e4 fixes suggestions given by the reviewer
da1e85c Adds gadget related API spec
c555cc1 Adds doodad related API spec
e5beb3e Adds api for update and delete of widgets
c43bade Adds api for creating widgets
deaa962 Adds all get methods for listing widgets
9de79ab Adds api for showing a widget and simple data model
8288ab1 Adds api framework for widget service
```

You know that's a mess, so you try to fix it by running `git rebase -i master` and squashing everything together...and you find yourself stuck in an endless maze of merge conflicts. There has to be a better way!

*(voiceover: there is a better way...)*

## Option 1: merge --squash

In this method, you will create a temporary branch and use `git merge --squash` to squash together the changes in your pull request.

1. Check out a new branch based on `master` (or the appropriate base branch if your feature branch isn't based on `master`):

    ```
    git checkout -b work master
    ```

    (This creates a new branch called `work` and makes that your current branch.)

1. Bring in the changes from your messy pull request using `git merge --squash`:

    ```
    git merge --squash my_feature
    ```

    This brings in all the changes from your `my_feature` branch and stages them, but does not create *any* commits.

3. Commit the changes with an appropriate commit message:

    ```
    git commit
    ```

    At this point, your `work` branch should be identical to the original `my_feature` branch (running `git diff my_feature_branch` should not show any changes), but it will have only a single commit after `master`.

4. Return to your feature branch and `reset` it to the squashed version:

    ```
    git checkout my_feature
    git reset --hard work
    ```

5. Update your pull request:

    ```
    git push -f
    ```

6. Optionally clean up your work branch:

    ```
    git branch -D work
    ```

## Option 2: Using `git commit-tree`

In this method, you will use `git commit-tree` to create a new commit without requiring a temporary branch.

1. Use `git commit-tree` to create new commit that reproduces the current state of your `my_feature` branch but 

    ```
    git commit-tree -p master -m 'this implements my_feature' my_feature^{tree}
    ```

    This uses the current state of the `my_feature` branch as the source of a new commit whose parent is `master`.  This will print out a commit hash:

    ```
    1d3917a3b7c43f4585084e626303c9eeee59c6d6
    ```

2. Reset your `my_feature` branch to this new commit hash:

    ```
    git reset --hard 1d3917a3b7c43f4585084e626303c9eeee59c6d6
    ```

3. Consider editing your commit message to meet [best practices][].

4. Update your pull request:

    ```
    git push -f
    ```

[best practices]: {{< ref "git-etiquette-commit-messages" >}}
