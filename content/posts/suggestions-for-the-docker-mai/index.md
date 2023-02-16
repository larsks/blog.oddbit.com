---
aliases:
- /2015/04/27/suggestions-for-the-docker-maintainer-directive/
- /post/2015-04-27-suggestions-for-the-docker-maintainer-directive
categories:
- tech
date: '2015-04-27'
tags:
- docker
title: Suggestions for the Docker MAINTAINER directive
---

Because nobody asked for it, this is my opinion on the use of the
`MAINTAINER` directive in your Dockerfiles.

The [documentation][] says simply:

    The MAINTAINER instruction allows you to set the Author field of the generated images.

[documentation]: https://docs.docker.com/reference/builder/#maintainer

Many people end up putting the name and email address of an actual
person here.  I think this is ultimately a bad idea, and does a
disservice both to members of a project that produce Docker images and
to people consuming those images.

1. Your image probably has (or will have) more than one "maintainer"

    Any non-trivial project is going to have more than one person
    contributing to things.  If you are the original creator of a
    Dockerfile, but later on someone else starts making some changes,
    which of you is the "maintainer"?

    Furthermore, asserting individual ownership over something that is
    better off being maintained collectively tends to discourage
    people from making changes (oh, this belongs to Bob, I'd better not
    touch it...).

1. Individual contributors may feel overwhelmed

    The individual responsible for creating a Docker image may or may be
    great at communicating with consumers.  If all questions about an
    image are going into a well-intentioned by ultimately unresponsive
    black hole, nobody is going to be happy.

1. Individual contributors come and go

    Most open source projects have fluid membership.  Someone who is
    around now and actively maintaining things may not be around several
    months down the road.  Having an absentee member listed as the
    "maintainer" of your images means that email about those images will
    probably not reach anybody in a position to respond.

1. Your project probably has a bug tracker

    Most projects have some sort of bug tracking mechanism available.
    These are generally in place both to keep track of the bug reports
    and support requests coming in as well as acting as a mechanism to
    distribute the work involved in responding to them to all members of
    a project.

    Ideally, you want questions about any images you maintain to go
    through the same tracking mechanism.

For all of these reasons, the `MAINTAINER` field of your Dockerfiles
should point to either a web site URL or to a common project email
address that goes into a bug tracker or is at least distributed to
more than one person.