---
categories: [tech]
aliases: ["/2014/09/02/visualizing-heat-stacks/"]
title: Visualizing Heat stacks
date: "2014-09-02"
tags:
  - openstack
  - heat
---

I spent some time today learning about Heat [autoscaling groups][],
which are incredibly nifty but a little opaque from the Heat command
line, since commands such as `heat resource-list` don't recurse into
nested stacks.  It is possible to introspect these resources (you can
pass the physical resource id of a nested stack to `heat
resource-list`, for example)...

...but I really like visualizing things, so I wrote a quick hack
called [dotstack][] that will generate [dot][] language output from a
Heat stack.  You can process this with [Graphviz][] to produce output
like this, in which graph nodes are automatically colorized by
resource type:

{{< figure
src="sample.svg"
link="sample.svg"
width="400"
>}}

Or like this, in which each node contains information about its
resource type and physical resource id:

{{< figure
src="sample-detailed.svg"
link="sample-detailed.svg"
width="400"
>}}

The source code is available on [github][dotstack].

[dot]:  http://en.wikipedia.org/wiki/DOT_(graph_description_language)
[graphviz]: http://www.graphviz.org/
[dotstack]: http://github.com/larsks/dotstack
[autoscaling groups]: https://wiki.openstack.org/wiki/Heat/AutoScaling

