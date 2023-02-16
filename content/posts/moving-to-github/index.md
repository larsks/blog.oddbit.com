---
categories: [tech]
aliases: ["/2013/11/13/moving-to-github/"]
title: Moving to GitHub
date: "2013-11-13"
tags:
  - blog
---

This blog has been hosted on [scriptogram][] for the past year or so.
Unfortunately, while I like the publish-via-Dropbox mechanism, there
have been enough problems recently that I've finally switched over to
using [GitHub Pages][] for hosting.  I've been thinking about doing
this for a while, but the things that finally pushed me to make the
change were:

- Sync problems that would prevent new posts from appearing (and that
  at least once caused posts to disappear).
- Lack of any response to bug reports by the site maintainers.

A benefit of the publish-via-Dropbox mechanism is, of course, that I
already had all the data and didn't need to go through any sort of
export process.

<!-- more -->

## Fixing metadata

Like [scriptogram][], [GitHub Pages][] is also a Markdown-based
solution.  GitHub uses [Jekyll][] to render Markdown to HTML, which
requires some metadata at the beginning of each post.  On
[scriptogram][] the file headers looked like this:

    Title: A random collection of OpenStack Tools
    Date: 2013-11-12
    Tags: openstack

Whereas the corresponding header for GitHub would look like this:

    ---
    layout: post
    title: A random collection of OpenStack Tools
    date: 2013-11-12
    tags:
      - openstack
    ---

I was able to generally automate this with the following script:

    #!/bin/sh

    for post in "$@"; do
      sed -i '
      1,/^$/ {
        1 i\---
        1 i\layout: post

        s/Title:/title:/
        s/Date:/date:/
        s/Tags:/tags:/

        /^$/ i\---
      }
      ' $post
    done

The `tags:` header need further processing to transform them into a
[YAML][] list.  That means something like:

    tags: foo,bar,baz

Would need to end up looking like:

    tags:
      - foo
      - bar
      - baz

While that's not entirely accurate -- YAML supports multiple list
syntaxes and I could have just expressed that as `[foo,bar,baz]` --  I
prefer this extended syntax and got there via the following `awk`
script:

    BEGIN {state=0}

    state == 1 && /^tags:/ {
      tags=$2
      next
    }

    state == 1 && /^---$/ {
      if (tags) {
        split(tags, taglist, ",")
        print "tags:"
        for (t in taglist)
          print "  -", taglist[t]
      }

      state=2
    }

    state == 0 && /^---$/ { state=1 }

    {print}

(This would process a single post; I wrapped it in a shell script to
run it across all the posts.)

# Redirecting legacy links

In order to preserve links pointing at the old blog I needed to generate
a bunch of HTML redirect files.  [Scriptogram][] posts had permalinks
of the form `/post/<slug>`, where `<slug>` was computed from the post
aliases: ["/2013/11/13/moving-to-github/"]
title.  GitHub posts (with `permalinks: pretty`) have the form
`/<year>/<month>/<day>/<title>`, where `<title>` comes from the
filename rather than the post metadata.

I automated the generation of redirects with the following script:

    #!/bin/sh

    for post in _posts/*; do
      # read the title from the post metadata
      title=$(grep '^title:' $post)
      title=${title/title: /}

      # convert the title from the metadata into the slug
      # used by scriptogram
      slug=${title,,}
      slug=${slug// /-}
      slug=${slug//[.,:?\/\'\"]/}

      # parse the post filename into year, month, day, and title
      # as used by github
      post_name=${post/_posts\//}
      post_date=${post_name:0:10}
      post_title=${post_name:11}
      post_title=${post_title:0:$(( ${#post_title} - 3))}
      post_year=${post_date%%-*}
      tmp=${post_date#*-}
      post_month=${tmp%%-*}
      post_day=${post_date##*-}

      # the url at which the post is available on github
      new_url="/$post_year/$post_month/$post_day/$post_title/"
      
      # generate the html redirect file
      mkdir -p post/$slug
      sed "s|URL|$new_url|g" redirect.html > post/$slug/index.html
    done

Where `redirect.html` looks like this:

    <!DOCTYPE html>
    <html>
    <head>
    <link rel="canonical" href="URL"/>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta http-equiv="refresh" content="0;url=URL" />
    </head>
    </html>

So given a file `_posts/2013-11-12-a-random-collection.md`, this would
result in a new file
`post/a-random-collection-of-openstack-tools/index.html` with the
following content:

    <!DOCTYPE html>
    <html>
    <head>
    <link rel="canonical" href="/2013/11/12/a-random-collection/"/>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta http-equiv="refresh" content="0;url=/2013/11/12/a-random-collection/" />
    </head>
    </html>

With this in place, a URL such as <http://blog.oddbit.com/post/a-random-collection-of-openstack-tools> goes to the right place.

**Update**: It turns out that it has been almost exactly a year since
I [moved from Blogger to Scriptogram][lastmigrate].

[scriptogram]: http://scriptogr.am/
[github pages]: http://pages.github.com/
[jekyll]: http://jekyllrb.com/
[yaml]: http://en.wikipedia.org/wiki/YAML
[lastmigrate]: http://blog.oddbit.com/2012/11/06/moving-from-blogger/

