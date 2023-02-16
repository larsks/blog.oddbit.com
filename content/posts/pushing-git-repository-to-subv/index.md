---
aliases:
- /2010/05/11/pushing-git-repository-to-subversion/
- /post/2010-05-11-pushing-git-repository-to-subversion
categories:
- tech
date: '2010-05-11'
tags:
- git
- subversion
- vcs
title: Pushing a Git repository to Subversion
---

I recently set up a git repository server (using [gitosis][1] and [gitweb][2]). Among the required features of the system was the ability to publish the git repository to a read-only Subversion repository. This sounds simple in principle but in practice proved to be a bit tricky.

Git makes an excellent Subversion client. You can use the git svn ... series of commands to pull a remote Subversion repository into a local git working tree and then have all the local advantages of git forcing the central code repository to change version control software. An important aspect of this model is that:

  - The Subversion repository is the primary source of the code, and
  - You populate your local git repository by pulling from the remote Subversion repository.

It is possible to push a git change history into an empty Subversion repository. Most instructions for importing a git repository look something like this, and involve replaying your git change history on top of the Subversion change history:

  - svn mkdir $REPO/{trunk, tags, branches}
  - git svn init -s $REPO
  - git svn fetch
  - git rebase trunk
  - git svn dcommit

This works, and is fine as long as there are no other clones of your git repository out there. The mechanism outlined here has a fatal flaw: it modifies the change history of the _master_ branch. If you were working in a clone of a remote git repository and you were to run git status after the above steps, you would see something like:
    
    
    # On branch master
    # Your branch and 'origin/master' have diverged,
    # and have 3 and 2 different commit(s) each, respectively.
    

If you were then to try to push this to the remote repository, you would get an error:
    
    
    $ git push
    To .../myrepo:
     ! [rejected]        master -> master (non-fast forward)
    error: failed to push some refs to '.../myrepo'
    

In cases where the git change history is shared with other git repositories, we need a solution that does not modify the _master_ branch. We can get this my modifying the procedure slightly.

The initial sequence is still the same:

  - svn mkdir $REPO/{trunk, tags, branches}
  - git svn init -s $REPO
  - git svn fetch

But instead of rebasing onto the _master_ branch, we create a local branch for managing the synchronization:

  - git checkout -b svnsync
  - git rebase trunk
  - git svn dcommit

At this point we have changed the history of the _svnsync_ branch and we have left the _master_ branch untouched. Subsequent updates look like this:

  - git checkout master
  - git pull
  - git checkout svnsync
  - git rebase master
  - git rebase trunk
  - git svn dcommit

This gives us what we want: we can publish our git repository to a Subversion repository while maintaining the shared change history among our existing git clones.

[1]: http://scie.nti.st/2007/11/14/hosting-git-repositories-the-easy-and-secure-way
[2]: https://git.wiki.kernel.org/index.php/Gitweb