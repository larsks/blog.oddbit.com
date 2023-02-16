---
categories: [tech]
aliases: ["/2013/11/22/automatic-maintenanc/"]
title: Automatic maintenance of tag feeds
date: "2013-11-22"
tags:
  - blog
  - git
---

I recently added some scripts to automatically generate tag feeds for
my blog when pushing new content.  I'm using GitHub Pages to publish
everything, so it seemed easiest to make tag generation part of a
`pre-push` hook (new in Git 1.8.2).  This hook is run automatically as
part of the `git push` operation, so it's the perfect place to insert
generated content that must be kept in sync with posts on the blog.

<!-- more -->

## Keeping things in sync

The `_posts` directory of my blog is a [git submodule][], which means
it gets updated and pushed asynchronously with respect to the main
repository.  We want to make sure that we don't regenerate the tag
feeds if there are either uncomitted changes in `_posts` *or* if there
are *unpushed* changes in `_posts`: in either situation, we could
generate a tag feed for tags that weren't actually used in any
published posts.

[git submodule]: http://git-scm.com/book/en/Git-Tools-Submodules

The following checks for any uncomitted changes in `_posts`:

    if ! git diff-files --quiet _posts; then
      echo "posts are out of sync (skipping tag maintenance)"
      exit 0
    fi

This will abort the tag feed generation if any of the following is
true:

- `_posts` has uncomitted changes
- `_posts` has new, untracked content
- `_posts` is at a revision that differs from the last comitted
  revision in the parent repository.

This still leaves one possible failure mode: if we commit all changes
in `_posts`, and then commit the updated `_posts` revision in the
parent repository, all of the previous checks will pass...but since we
haven't pushed the `_posts` repository, we could still be pushing tags
that don't match up with published posts.

The following check will prevent this situation by checking if the
repository differs from the upstream branch:

    if ! (cd _posts; git diff-index --quiet origin/posts); then
      echo "posts are out of sync (skipping tag maintenance)"
      exit 0
    fi

## Generating tag feeds

In order to prevent stale tags, we need to delete and regenerate all
the tag feeds.  Cleaning up the existing tag feeds is taken care of by
the `cleantagfeeds` script:

    echo "cleaning tag feeds"
    _oddbit/cleantagfeeds

Which is really just a wrapper for the following `find` commands:

    #!/bin/sh

    # Delete tag feeds unless there is a `.keep` file in the
    # same directory.
    find tag/* -name index.xml \
      -execdir sh -c 'test -f .keep || rm -f index.xml' \;
    find tag/* -type d -delete

This will preserve any tag feeds that have a corresponding `.keep`
file (just in case we've done something special that requires manual
intervention) and deletes everything else.

Generating the tag feeds is taken care of by the `gentagfeeds`
script:

    echo "generating tag feeds"
    _oddbit/gentagfeeds

This is a Python program that iterates over all the files in `_posts`,
reads in the YAML frontmatter from each one, and then generates a feed
file for each tag using a template.

Finally, we need to add any changes to the repository.  We
unilaterally add the `tags/` directory:

    git add -A tag

And then see if that got us anything:

    if ! git diff-index --quiet HEAD -- tag; then
      git commit -m 'automatic tag update' tag
    fi

At this point, we've regenerated all the tag feeds and committed any
new or modified tag feeds to the repository, which will get published
to GitHub as part of the current `push` operation.

The actual feed templates look like this:

    ---
    layout: rss
    exclude: true
    tags:
      - {{tag}}
    ---

I'm using a modified version of [gh-pages-blog][] in which I have
modified `_layouts/rss.xml` to optionally filter posts by tag using
the following template code:

{% raw %}
      .
      .
      .
			{% for p in site.posts %}
        {% if page contains 'tags' %}
          {% assign selected = false %}
          {% for t in p.tags %}
            {% if page.tags contains t %}
              {% assign selected = true %}
            {% endif %}
          {% endfor %}

          {% if selected == false %}
          {% continue %}
          {% endif %}
        {% endif %}
      .
      .
      .
{% endraw %}

For each post on the site (`site.posts`), this checks for any overlap
between the tags in the post and the tags selected in the tag feed.
While the automatic feeds use only a single tag, this also makes it
possible to create feeds that follow multiple tags.

All of the code used to implement this is available in the [GitHub
repository for this blog][repo].

[repo]: http://github.com/larsks/blog.oddbit.com/
[gh-pages-blog]: https://github.com/thedereck/gh-pages-blog/

