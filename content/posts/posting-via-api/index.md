---
categories: [tech]
aliases: ["/2012/11/05/posting-via-api/"]
title: Posting to Scriptogr.am using the API
date: "2012-11-05"
tags:
  - scriptogr.am
  - api
---

Scriptogr.am has a [very simple api][api] that allows one to `POST` and
`DELETE` articles.  `POST`ing an article will place it in the
appropriate Dropbox directory and make it available on your blog all
in one step.

Here is how you could use this API via Curl:

    curl \
           -d app_key=$APP_KEY \
           -d user_id=$USER_ID \
           -d name="${title:-$1}" \
           --data-urlencode text@$tmpfile \
           \
           http://scriptogr.am/api/article/post/

This assumes that you've registered for an application key and that
you have configured the value into `$APP_KEY` and your Scriptogr.am
user id into `$USER_ID`.

The `name` attribute is both the title of your article *and also* the
filename (normalized and with a `.md` extension).  Your article *must
not* contain the metadata values that are allowed when you're editing
files directly in the Dropbox directory.

[api]: http://scriptogr.am/dashboard/#api_documentation

