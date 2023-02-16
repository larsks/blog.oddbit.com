---
categories: [tech]
aliases: ["/2012/11/06/convert-html-to-markdown/"]
title: Converting HTML to Markdown
date: "2012-11-06"
tags:
  - markdown
  - meta
---

In order to import posts from [Blogger][] into [Scriptogr.am][] I needed to convert all the HTML formatting into Markdown.  Thankfully there are a number of tools out there that can help with this task.

- [MarkdownRules][]. This is an online service build around
  [Markdownify][].  It's a slick site with a nice API, but the backend
  wasn't able to correctly render `<pre>` blocks.  Since I'm often
  writing about code, my posts are filled with things like embedded
  XML and `#include <stdio.h>`, so this was a problem.

- [Pandoc][].  This is a general purpose tool that can convert between
  a variety of markup formats.  Unfortunately, it *also* had similar
  problems with `<pre>` blocks.

- [html2text][].  This a Python tool that converts HTML to Markdown.
  It seems to do a better job at handling the `<pre>` blocks, although
  it doesn't always get the indent level correct when the `<pre>`
  blocks are embedded in lists.

I ultimately ended up using [html2text][], combined with a [simple
script][] to read the [export from Blogger][] and feed each document to
the converter.

[markdownify]: http://milianw.de/projects/markdownify/
[markdownrules]: http://markdownrules.com/
[html2text]: https://github.com/aaronsw/html2text
[blogger]: http://blogger.com/
[scriptogr.am]: http://scriptogr.am/
[simple script]: https://gist.github.com/4022537
[pandoc]: http://johnmacfarlane.net/pandoc/
[export from blogger]: http://www.dataliberation.org/takeout-products/blogger

