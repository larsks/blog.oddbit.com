---
categories: [tech]
aliases: ["/2013/11/17/json-tools/"]
title: "json-tools: cli for generating and filtering json"
date: "2013-11-17"
tags:
  - json
  - openstack
---
Interacting with JSON-based APIs from the command line can be
difficult, and OpenStack is filled with REST APIs that consume or
produce JSON.   I've just put pair of tools for generating and
filtering JSON on the command line, called collectively
[json-tools][].

Both make use of the Python [dpath][] module to populate or filter
JSON objects.

The `jsong` command generates JSON on `stdout`.  You provide `/`-delimited paths
on the command line to represent the JSON structure.  For example, if
you run:

    $ jsong auth/passwordCredentials/username=admin \
      auth/passwordCredentials/password=secret

You get:

    {
        "auth": {
            "passwordCredentials": {
                "username": "admin", 
                "password": "secret"
            }
        }
    }

The `jsonx` command accepts JSON on `stdin` and selects subtrees or
values for output on `stdout`.  Given the above output, you could
extract the password with:

    jsonx -v auth/passwordCredentials/password

Which would give you:

    secret

The `-v` flag here indicates that you only want the values of matched
paths; without the `-v` the output would have been:

    auth/passwordCredentials/password secret

There are more examples -- including some use of the OpenStack APIs --
in the [README] document.

[json-tools]: http://github.com/larsks/json-tools/
[dpath]: https://github.com/akesterson/dpath-python
[README]: https://github.com/larsks/json-tools/blob/master/README.md

