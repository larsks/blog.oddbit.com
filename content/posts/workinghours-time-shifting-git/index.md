---
aliases:
- /2015/04/10/workinghours-time-shifting-git-commits/
- /post/2015-04-10-workinghours-time-shifting-git-commits
categories:
- tech
date: '2015-04-10'
tags:
- git
- hack
- bad_ideas
title: 'Using tools badly: time shifting git commits with Workinghours

  '
---

This is a terrible hack.  If you are easily offended by bad ideas
implemented poorly, move along!

You are working on a wonderful open source project...but you are not
*supposed* to be working on that project! You're supposed to be doing
your *real* work!  Unfortunately, your extra-curricular activity is
well documented in the git history of your project for all to see:

![Heatmap of original commit history][repo-before.png]

And now your boss knows why the TPS reports are late.  You need
[workinghours][], a terrible utility for doing awful things to your
repository history.  [Workinghours][] will programatically time shift
your git commits so that they appear to have happened within specified
time intervals (for example, "between 7PM and midnight").

[workinghours]: https://github.com/larsks/workinghours.git

Running `workinghours` on your repository makes things better:

    workinghours --afterhours | workinghours-apply

And now you have:

![Heatmap of modified commit history][repo-after.png]

But that looks suspicious.  What are you, some kind of machine?
Fortunately, `workinghours` has a `--drift` option that will introduce
some variety into your start and end times.  The syntax is `--drift P
before after`, where for each commit `workinghours` will with
probability *P* extend the beginning of the time interval by a random
amount between 0 and *before*
hours, and the end of the time interval by a random amount between 0
and *after* hours.

Introducing a low probability drift to the beginning of the interval:

    workinghours --afterhours -d 0.2 8 2 | workinghours-apply

Gives us:

![Heatmap of modified commit history][repo-drifted.png]

Congratulations, you are a model employee.

[repo-before.png]: repo-before.png
[repo-after.png]: repo-after.png
[repo-drifted.png]: repo-drifted.png
