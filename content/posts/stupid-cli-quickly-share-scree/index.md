---
aliases:
- /2014/09/23/stupid-cli-quickly-share-screencap/
- /post/2014-09-23-stupid-cli-quickly-share-screencap
categories:
- tech
date: '2014-09-23'
tags:
- cli
title: 'Stupid command line tricks: Quickly share screen captures'
---

Sometimes you want to quickly share a screenshot with someone.  Here's
my favorite mechanism, which assumes you have installed both `curl`
and the [ImageMagick][] suite.

[imagemagick]: http://www.imagemagick.org/

    $ import png:- | curl -T- -s chunk.io
    http://chunk.io/f/76ea98ea081748e19de4507fde3c2c65  

When you run this command, you cursor will change into crosshairs.
Click on a window, and this will grab a png image of that window and
send it to [chunk.io](http://chunk.io/) using curl.

You'll get back a URL that you can use to share the image with people.