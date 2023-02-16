---
date: 2021-09-05
categories:
  - tech
tags:
  - stackexchange
  - browser
  - javascript
  - userscripts
title: A pair of userscripts for cleaning up Stack Exchange sites
---

I've been a regular visitor to [Stack Overflow][] and other [Stack
Exchange][] sites over the years, and while I've mostly enjoyed the
experience, I've been frustrated by the lack of control I have over
what questions I see. I'm not really interested in looking at
questions that have already been closed, or that have a negative
score, but there's no native facility for filtering questions like
this.

[stack overflow]: https://stackoverflow.com
[stack exchange]: https://stackexchange.com

I finally spent the time learning just enough JavaScript ~~~to hurt
myself~~~ to put together a pair of scripts that let me present the
questions that way I want:

## sx-hide-questions

The [sx-hide-questions][] script will hide:

- Questions that are closed
- Questions that are marked as a duplicate
- Questions that have a score below 0

Because I wanted it to be obvious that the script was actually doing
something, hidden questions don't just disappear; they fade out.

These behaviors (including the fading) can all be controlled
individually by a set of global variables at the top of the script.

[sx-hide-questions]: https://github.com/larsks/sx-question-filter/raw/master/sx-hide-questions.user.js

{{< figure src="fading.gif" >}}

## sx-reorder questions

The [sx-reorder-questions][] script will sort questions such that
anything that has an answer will be at the bottom, and questions that
have not yet been answered appear at the top.

[sx-reorder-questions]: https://github.com/larsks/sx-question-filter/raw/master/sx-reorder-questions.user.js

## Installation

If you are using the [Tampermonkey][] extension, you should be able to
click on the links to the script earlier in this post and be taken
directly to the installation screen. If you're *not* running
Tampermonkey, than either (a) install it, or (b) you're on your own.

[tampermonkey]: https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo?hl=en

You can find both of these scripts in my [sx-question-filter][]
repository.

## Caveats

These scripts rely on the CSS classes and layout of the Stack Exchange
websites. If these change, the scripts will need updating. If you
notice that something no longer works as advertised, please feel free
to submit pull request with the necessary corrections!


[sx-question-filter]: https://github.com/larsks/sx-question-filter
