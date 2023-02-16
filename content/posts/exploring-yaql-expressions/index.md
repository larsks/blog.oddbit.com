---
categories: [tech]
aliases: ["/2016/08/11/exploring-yaql-expressions/"]
title: "Exploring YAQL Expressions"
date: "2016-08-11"
tags:
  - openstack
  - heat
  - hot
  - yaql
---

The Newton release of [Heat][] adds support for a [yaql][yaql_func]
intrinsic function, which allows you to evaluate [yaql][] expressions
in your Heat templates.  Unfortunately, the existing yaql
documentation is somewhat limited, and does not offer examples of many
of yaql's more advanced features.

[heat]: https://wiki.openstack.org/wiki/Heat
[yaql]: https://yaql.readthedocs.io/en/latest/
[yaql_func]: http://docs.openstack.org/developer/heat/template_guide/hot_spec.html#yaql

I am working on a [Fluentd][] composable service for [TripleO][].  I
want to allow each service to specify a logging source configuration
fragment, for example:

[fluentd]: http://www.fluentd.org/
[tripleo]: https://wiki.openstack.org/wiki/TripleO

    parameters:
      NovaAPILoggingSource:
        type: json
        description: Fluentd logging configuration for nova-api.
        default:
          tag: openstack.nova.api
          type: tail
          format: |
            /(?<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d+) (?<pid>\d+) (?<priority>\S+) (?<message>.*)/
          path: /var/log/nova/nova-api.log
          pos_file: /var/run/fluentd/openstack.nova.api.pos

This generally works, but several parts of this fragment are going to
be the same across all OpenStack services.  I wanted to reduce the
above to just the unique attributes, which would look something like:

    parameters:
      NovaAPILoggingSource:
        type: json
        description: Fluentd logging configuration for nova-api.
        default:
          tag: openstack.nova.api
          path: /var/log/nova/nova-api.log

This would ultimately give me a list of dictionaries of the form:

    [
      {
        "tag": "openstack.nova.api",
        "path": "/var/log/nova/nova-api.log"
      },
      {
        "tag": "openstack.nova.scheduler",
        "path": "/var/log/nova/nova-scheduler.log"
      }
    ]

I want to iterate over this list, adding default values for attributes
that are not explicitly provided.

The yaql language has a `select` function, somewhat analagous to the
SQL `select` statement, that can be used to construct a new data
structure from an existing one.  For example, given the above data in
a parameter called `sources`, I could write:

    outputs:
      sources:
        yaql:
          data:
            sources: {get_param: sources}
          expression: >
            $.data.sources.select({
              'path' => $.path,
              'tag' => $.tag,
              'type' => $.get('type', 'tail')})

This makes use of the `.get` method to insert a default value of
`tail` for the `type` attribute for items that don't specify it
explicitly.  This would produce a list that looks like:

    [
        {
            "path": "/var/log/nova/nova-api.log",
            "tag": "openstack.nova.api",
            "type": "tail"
        },
        {
            "path": "/var/log/nova/nova-scheduler.log",
            "tag": "openstack.nova.scheduler",
            "type": "tail"
        }
    ]

That works fine, but what if I want to parameterize the default value
such that it can be provided as part of the template?  I wanted to be
able to pass the yaql expression something like this...

    outputs:
      sources:
        yaql:
          data:
            sources: {get_param: sources}
            default_type: tail

...and then within the yaql expression, insert the value of
`default_type` into items that don't provide an explicit value for the
`type` attribute.

This is trickier than it might sound at first because within the
context of the `select` method, `$` is bound to the *local* context,
which will be an individual item from the list.  So while I can ask
for `$.path`, there's no way to refer to items from the top-level
context.  Or is there?

The [operators][] documentation for yaql mentions the "context pass"
operator, `->`, but doesn't provide any examples of how it can be
used. It turns out that this operator will be the key to our solution.
But before we look at that in more detail, we need to introduce the
`let` statement, which can be used to define variables.  The `let`
statement isn't mentioned in the documentation at all, but it looks
like this:

[operators]: https://yaql.readthedocs.io/en/latest/getting_started.html#operators

    let(var => value, ...)

By itself, this isn't particularly useful.  In fact, if you were to
type a bare `let` statement in a yaql evaluator, you would get an
error:

    yaql> let(foo => 10, bar => 20)
    Execution exception: <yaql.language.contexts.Context object at 0x7fbaf9772e50> is not JSON serializable

This is where the `->` operator comes into play.  We use that to pass
the context created by the `let` statement into a yaql expression. For
example:

    yaql> let(foo => 10, bar => 20) -> $foo
    10
    yaql> let(foo => 10, bar => 20) -> $bar
    20

With that in mind, we can return to our earlier task, and rewrite the
yaql expression like this:

    outputs:
      sources:
        yaql:
          data:
            sources: {get_param: sources}
            default_type: tail
          expression: >
            let(default_type => $.data.default_type) ->
            $.data.sources.select({
              'path' => $.path,
              'tag' => $.tag,
              'type' => $.get('type', $default_type)})

Which will give us exactly what we want.  This can of course be
extended to support additional default values:

    outputs:
      sources:
        yaql:
          data:
            sources: {get_param: sources}
            default_type: tail
            default_format: >
              /some regular expression/
          expression: >
            let(
              default_type => $.data.default_type,
              default_format => $.data.default_format
            ) ->
            $.data.sources.select({
              'path' => $.path,
              'tag' => $.tag,
              'type' => $.get('type', $default_type),
              'format' => $.get('format', $default_format)
            })

Going out on a bit of a tangent, there is another statement not
mentioned in the documentation: the `def` statement lets you defined a
yaql function.  The general format is:

    def(func_name, func_body)

Where `func_body` is a yaql expresion.  For example:

    def(upperpath, $.path.toUpper()) ->
    $.data.sources.select(upperpath($))

Which would generate:

    [
        "/VAR/LOG/NOVA/NOVA-API.LOG", 
        "/VAR/LOG/NOVA/NOVA-SCHEDULER.LOG"
    ]

This obviously becomes more useful as you use user-defined functions
to encapsulate more complex yaql expressions for re-use.

Thanks to [sergmelikyan][] for his help figuring this out.

[sergmelikyan]: https://github.com/sergmelikyan
