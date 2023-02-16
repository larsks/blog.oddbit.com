---
aliases:
- /2010/01/29/cleaning-up-subversion-with-git/
- /post/2010-01-29-cleaning-up-subversion-with-git
categories:
- tech
date: '2010-01-29'
tags:
- svn
- versioncontrol
- git
- subversion
title: Cleaning up Subversion with Git
---

# Overview

At my office, we have a crufty [Subversion][1] repository (dating back to early 2006) that contains a jumble of unrelated projects. We would like to split this single repository up into a number of smaller repositories, each following the recommended trunk/tags/branches repository organization.

What we want to do is move a project from a path that looks like this:
    
    
    .../projects/some-project-name
    

To a new repository using the recommended Subversion repository layout, like this:
    
    
    .../some-project-name/trunk
    

Our lives are complicated by the fact that there has been a lot of mobility (renames/moves) of projects within the repository.

# Setup

We'll set up a test environment that will demonstrate the problem and our solution.

  1. Create the empty repositories:
    
    
        set -x
        rm -rf work && mkdir work
        cd work
        WORKDIR=$(pwd)
        mkdir repos
        
        # create source repository
        svnadmin create repos/src
        
        # create destination reposiory
        svnadmin create repos/dst
    

  2. Create our desired repository structure in the destination repository:
    
    
        svn mkdir -m 'create trunk' file://$WORKDIR/repos/dst/trunk
        svn mkdir -m 'create branches' file://$WORKDIR/repos/dst/branches
        svn mkdir -m 'create tags' file://$WORKDIR/repos/dst/tags
    

  3. Create a simple revision history:
    
    
        svn co file://$WORKDIR/repos/src src
        (
        cd src
        
        # Create our initial set of projects.
        mkdir projects
        mkdir projects/{project1,project2}
        touch projects/project1/{file11,file12}
        touch projects/project2/{file21,file22}
        svn add *
        svn ci -m 'initial commit'
        
        # Relocate a file between projects.
        svn mv projects/project1/file11 projects/project2/
        svn ci -m 'moved file11'
        
        # Rename a project.
        svn mv projects/project2 projects/project3
        svn update
        svn ci -m 'renamed project2 to project3'
        )
    

  4. We can see the structure of the source repository like this:
    
    
        echo "Contents of source reposiory:"
        svn ls -R file://$WORKDIR/repos/src
    

Your output should look something like this:
    
    
    projects/
    projects/project1/
    projects/project1/file12
    projects/project3/
    projects/project3/file11
    projects/project3/file21
    projects/project3/file22
    

In this example, we'll try to import _project3_ into a new repository.

# Using Subversion

With Subversion, it's easy to extract a single project from the repository:
    
    
    svn co file://$WORKDIR/repos/src/projects/project3
    

This gives us a directory called project3 containing the contents of the project. Unfortunately, there are no tools that will allow us to take this working copy and move it into another repository.

Subversion includes a tool called svnadmin that allows on to perform a number of operations on a Subversion repository, but it requires access to the filesystem instance of the repository (it will not work over the network). This is a substantial limitation if you are working with a repository that is maintained by someone else, but we have the necessary access to our repository.

The svnadmin command includes a dump operation that serializes a repository -- and its entire revision history -- into a text stream that can be loaded into another repository with a corresponding load operation. We don't want the entire repository, so we'll make use of the svndumpfilter command which, as you might expect, can apply certain filters to the output of svnadmin dump.

We might try something like this:
    
    
    svnadmin dump repos/src |
      svndumpfilter include projects/project3/ |
      svnadmin load repos/dst
    

Unforunately, this will fail with an error along the lines of:
    
    
    svndumpfilter: Invalid copy source path '/projects/project2'
    svnadmin: Can't write to stream: Broken pipe
    

And if you were to look at the destination repository, you would find projec3 entirely absent:
    
    
    echo "Contents of destination repository (after dump/filter/load):"
    svn ls -R file://$WORKDIR/repos/dst
    

And even if it worked we would still have to muck about in the destination repository to create our desired repository layout.

# Using Git

[Git][2] is another version control system, similar in some ways to [Subversion][1] but designed for distributed operation. If you're not familiar with git there is lots of documentation available online.

We'll start by checking out _project3_ from the Subversion repository:
    
    
    rm -rf project3
    git svn clone file://$WORKDIR/repos/src/projects/project3
    cd project3
    

Because we're going to import this code into a new repository we need to erase all references to the source repository:
    
    
    git branch -rD git-svn
    git config --remove-section svn-remote.svn
    rm -rf .git/svn
    

And now we associate this git repository with the destination Subversion repository:
    
    
    git svn init -s file://$WORKDIR/repos/dst
    git svn fetch
    

We now apply the revision history to the trunk of the destination repository and commit the changes:
    
    
    git rebase trunk
    git svn dcommit
    

After all of this, we have exactly what we want -- our project hosted in a new repository with our desired layout. The following commands show the contents of the repository:
    
    
    echo "Contents of destination repository (after git):"
    svn ls -R file://$WORKDIR/repos/dst
    

And produce output like this:
    
    
    branches/
    tags/
    trunk/
    trunk/file11
    trunk/file21
    trunk/file22
    

And the revision history of the project is available in the destination repository:
    
    
    echo "Revision history in destination repository:"
    svn log file://$WORKDIR/repos/dst
    

The output will look something like:
    
    
    Revision history in destination repository:
    + svn log file:///home/lars/projects/svn-to-svn-via-git/work/repos/dst
    ------------------------------------------------------------------------
    r7 | lars | 2009-06-03 14:46:02 -0400 (Wed, 03 Jun 2009) | 1 line
    
    renamed project2 to project3
    ------------------------------------------------------------------------
    r6 | lars | 2009-06-03 14:46:02 -0400 (Wed, 03 Jun 2009) | 1 line
    
    initial commit
    ------------------------------------------------------------------------
    r5 | (no author) | 2009-06-03 14:45:55 -0400 (Wed, 03 Jun 2009) | 1 line
    
    This is an empty revision for padding.
    ------------------------------------------------------------------------
    r4 | (no author) | 2009-06-03 14:45:53 -0400 (Wed, 03 Jun 2009) | 1 line
    
    This is an empty revision for padding.
    ------------------------------------------------------------------------
    r3 | lars | 2009-06-03 14:45:52 -0400 (Wed, 03 Jun 2009) | 1 line
    
    create tags
    ------------------------------------------------------------------------
    r2 | lars | 2009-06-03 14:45:52 -0400 (Wed, 03 Jun 2009) | 1 line
    
    create branches
    ------------------------------------------------------------------------
    r1 | lars | 2009-06-03 14:45:52 -0400 (Wed, 03 Jun 2009) | 1 line
    
    create trunk
    ------------------------------------------------------------------------
    

[1]: http://subversion.tigris.org/
[2]: http://git-scm.com/