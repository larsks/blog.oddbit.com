---
aliases:
- /2016/02/16/gruf-a-gerrit-command-line-utility/
- /post/2016-02-16-gruf-a-gerrit-command-line-utility
categories:
- tech
date: '2016-02-16'
tags:
- gerrit
- gruf
title: Gruf, a Gerrit command line utility
---

(See also [the followup]({{< ref "gruf-gets-superpowers" >}}) to this article.)

I've recently started spending more time interacting with [Gerrit][],
the code review tool used both by [OpenStack][], at
[review.openstack.org][], and by a variety of other open source projects
at GerritForge's GitHub-linked [review.gerrithub.io][].  I went
looking for command line tools and was largely disappointed with what
I found.  Many of the solutions out there assume that you're regularly
interacting with a single Gerrit instance, and that's seldom the case:
more often, the Gerrit server in use varies from project to project.  
I also found that many of the tools were opinionated in what sort of
output they would produce.

[gerrit]: https://www.gerritcodereview.com/
[review.openstack.org]: http://review.openstack.org/
[review.gerrithub.io]: http://review.gerrithub.io/

For these reasons, I ended up rolling my own tool called [Gruf][].
This is a wrapper for the Gerrit [command line API][api] that will let
you query and review Gerrit change requests from the comfort of your
command line.  It is meant to supplement, not replace, the
[git-review][] tool that can be used to submit code for review and
download patchsets for reviewing changes locally.

[gruf]: https://github.com/larsks/gruf
[api]: https://review.openstack.org/Documentation/cmd-index.html
[git-review]: https://github.com/openstack-infra/git-review

Gruf produces output by passing the result of Gerrit commands through
[Jinja][] templates, which means you can produce just about any sort
of output you want without needing to modify the code.

[jinja]: http://jinja.pocoo.org/

## Basic usage

You can use pretty much any of the Gerrit [user
commands][] as they are presented in the documentation.  For example,
to get a list of review requests that are owned by you:

    $ gruf query status:open owner:self
    262882   7   larsks   introduce global "nodes" configuration role

[user commands]: https://review.openstack.org/Documentation/cmd-index.html#user_commands

Or to review an existing review request:

    $ gruf review --code-review +2 262882

## Configuration

Gruf will attempt to read configuration information from
`$HOME/.config/gruf/gruf.yml` (unless `$XDG_CONFIG_DIR` in your
environment points somewhere other than `$HOME/.config`).  This is a
[YAML][] format file that can contain two keys:

- `querymap` -- contains query term aliases
- `cmdalias` -- contains command aliases

These are both discussed in more detail below.

## Templates

Gruf produces output by passing the response from Gerrit through a
template.  You can provide an explicit template name on the command
line using the `-t` flag.  The previous `gruf query` example is
exactly equivalent to:

    $ gruf -t default query status:open owner:self

But you can instead ask to see all of the comments for the results:

    $ gruf -t comments query status:open owner:self

Gruf looks for templates in two places:

- In the gruf module directory.
- In a `templates` directory co-located with your `gruf.yml`
  configuration file.

Within each directory, Gruf first looks for templates in a
subdirectory named after the Python class used to process the response
from Gerrit.  For the `query` command, this is `QueryResponse`; which
means that to override the default template for the `query` command,
you would create `$HOME/.config/gruf/templates/QueryResponse/default`.

You can also provide Gruf with inline templates using the
`--inline-template` (aka `-T`) command line option:

    $ gruf -T '{{url}}' query here limit:5
    https://review.gerrithub.io/263378
    https://review.gerrithub.io/263342
    https://review.gerrithub.io/263341
    https://review.gerrithub.io/263340
    https://review.gerrithub.io/263268

If you want to see what attributes are available in the response from
Gerrit, use the `yaml` template:

    $ gruf -t yaml query here limit:1

This will dump the results from Gerrit as a YAML document.

## Referring to changes

Gerrit itself allows you to refer to reviews using change numbers
("262882"), change IDs ("Id55e1baa0adf10f704dec2516e98a112be381d14"),
and git commit IDs ("80ce4ea09ab7c16aeb5b356ad17e8fb740f3d22b").

Gruf adds the option of using git reference names (e.g., branches and
tags) by prefixing a term with `git:`.  So if you want to get an
overview of a review associated with your current commit, you can ask
for `git:HEAD`:

    $ gruf -t patches query git:HEAD
    262882   larsks   introduce global "nodes" configuration role
                      https://review.gerrithub.io/262882

             [007] refs/changes/82/262882/7
                   rdo-ci-centos   Verified -1
             [006] refs/changes/82/262882/6
                   rdo-ci-centos   Verified -1
             [005] refs/changes/82/262882/5
                   rdo-ci-centos   Verified -1
             [004] refs/changes/82/262882/4
                   rdo-ci-centos   Verified -1
             [003] refs/changes/82/262882/3
                   rdo-ci-centos   Verified -1
             [002] refs/changes/82/262882/2
                   larsks          Code-Review -1
             [001] refs/changes/82/262882/1

This works for any other valid `git` reference (a relative reference
like `git:HEAD^`, a branch or tag name like `stable/liberty`, or whatever).

## Query aliases

The Gerrit query language supports a variety of query operators.  For
example, you can search for reviews that you own with `owner:self` and
you can limit results to a particular project with something like
`project:redhat-openstack/triple-quickstart`.  While that's very
useful, it can be annoying if you find yourself typing the same
operators over and over.

Gruf supports a simple form of query aliasing.  There are three
built-in aliases:

- `mine` expands to `owner:self`
- `open` expands to `status:open`
- `here` expands to `project:{project}`, where `{project}` is replaced
  by the name of the current project.

This allows you to simplify this:

    gruf query status:open project:redhat-openstack/tripleo-quickstart

Into:

    gruf query open here

You can define additional aliases in the `querymap` section of your
`gruf.yml` file.  For example, given the following:

    querymap:
      needsreview: status:open -is:reviewed

You can now find changes in the project that need review by running:

    gruf query needsreview here

## Command aliases

You may get tired of typing:

    gruf -t patches query ...

If you create the following entry in your `gruf.yml` configuration
file:

    cmdalias:
      patches:
        cmd: query
        template: patches

You can now type something like:

    gruf patches git:HEAD

And gruf will behave as if you typed:

    gruf -t patches query git:HEAD

This is especially useful for simple inline templates.  For example,
given the following entry:

    refs:
      cmd: query
      inline_template: >-
        {{number}}
        {{currentPatchSet.ref}}
        {{currentPatchSet.revision}}

You can type:

    gruf refs open here

And get output like:

    262882 refs/changes/82/262882/7 80ce4ea09ab7c16aeb5b356ad17e8fb740f3d22b
    263336 refs/changes/36/263336/2 5600951b5ce6e18b3d3fff75599518a00ea25384
    263241 refs/changes/41/263241/1 27dbb595d58372b396cafe6dfacf97e58f43bc26
    260561 refs/changes/61/260561/4 ee7f35d0528894990b736b8cece338d1c57ab0ac
    262397 refs/changes/97/262397/1 6181c9b7361e4a804ab7069491a0780d119144f6
    261934 refs/changes/34/261934/1 cf84db84bb67f201df5b59bbdf831dcf3d83056d
    261218 refs/changes/18/261218/1 0d383494c579932e1edddfed23755da7fb2c9aae

## Example

The following example session assumes the following configuration:

    cmdalias:
      comments:
        cmd: query
        template: comments
      patches:
        cmd: query
        template: patches

- Get a list of open reviews:

        $ gruf query open here
        262882   7   larsks   introduce global "nodes" configuration role
        263336   2   trown    WIP refactor and simplify image build
        263241   1   trown    Move mention of pre-downloaded image to lower section of README
        260561   4   trown    Make release rpm location configurable
        262397   1   sshnaidm Split mitaka installation playbook
        261934   1   trown    WIP Use IPA ramdisk for liberty deploy
        261218   1   trown    WIP self writing docs

- See an overview of patch sets for a particular change:

        $ gruf patches 262882
        262882   larsks   introduce global "nodes" configuration role
                          https://review.gerrithub.io/262882

                 [007] refs/changes/82/262882/7
                       rdo-ci-centos   Verified -1
                 [006] refs/changes/82/262882/6
                       rdo-ci-centos   Verified -1
                 [005] refs/changes/82/262882/5
                       rdo-ci-centos   Verified -1
                 ...

- See comments for a particular change:

        $ gruf comments 262882
        ...
        From: Lars Kellogg-Stedman (larsks) <lars@redhat.com>

            Uploaded patch set 7.

        From:  (rdo-ci-centos) <whayutin+ci_centos@redhat.com>

            Patch Set 7: Verified-1
            
            Build Failed 
            
            https://ci.centos.org/job/tripleo-quickstart-gate-liberty-delorean-ha/86/ : Test failed
            
            https://ci.centos.org/job/tripleo-quickstart-gate-mitaka-delorean-ha/94/ : Test failed
            
            https://ci.centos.org/job/tripleo-quickstart-gate-mitaka-delorean-minimal/97/ : Test failed
            
            https://ci.centos.org/job/tripleo-quickstart-gate-liberty-delorean-minimal/99/ : Test failed
            
            https://ci.centos.org/job/trown-poc-tripleo-quickstart-gate-quickstart/22/ : Test ran successfully

- Abandon a change (with a comment):

        $ gruf review -m 'this was a terrible idea' --abandon 262882,7

## Future plans

I've already started using this regularly myself, but I'm sure that as
I work with Gerrit I will develop a better understanding of what I
want in a command-line tool.  At the very least I need to implement
some form of caching to avoid hammering the Gerrit servers with
repeated requests for the same information.

Beyond that, I'm curious if anyone else finds this useful and if there
are features you would like to see.

Happy hacking!

[openstack]: http://openstack.org/
[yaml]: http://yaml.org/
