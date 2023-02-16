---
categories: [tech]
aliases: ["/2010/02/10/filtering-blogger-feeds/"]
title: Filtering Blogger feeds
date: "2010-02-10"
tags:
  - pipes
  - rss
  - atom
  - blogger
  - filter
---

After encountering a number of problems trying to filter Blogger feeds by tag (using services like [Feedrinse][1] and Yahoo [Pipes][2]), I've finally put together a solution that works:

*   Shadow the feed with [Feedburner][3].
*   Enable the *Convert Format Burner*, and convert your feed to RSS 2.0.
*   Use Yahoo [Pipes][2] to filter the feed (because Feedrinse seems to be broken).

This let me create a feed that excluded all my posts containing the *fbpost* tag, thus allowing me to avoid yet another postgasm in Facebook when adding new import URL to notes.

While fiddling with this I came across [this article][4] that discusses a number of tools (some no longer available) for processing RSS feeds.

[1]: http://feedrinse.com/
[2]: http://pipes.yahoo.com/
[3]: http://feedburner.com/
[4]: http://www.tothepc.com/archives/10-tools-to-combine-mix-blend-multiple-rss-feeds/
